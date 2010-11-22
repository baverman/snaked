author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Snippets'
desc = "SnipMate's clone"

import os.path
import re

import weakref
import gtk, gobject

from gtksourceview2 import CompletionProvider, CompletionProposal
from gtksourceview2 import COMPLETION_ACTIVATION_USER_REQUESTED

from snaked.util import idle
from .parser import parse_snippets_from

loaded_snippets = {}
existing_snippet_contexts = {'not_initialized':True}
snippets_match_hash = {}
completion_providers = {}

stop_managers = weakref.WeakKeyDictionary()

def editor_opened(editor):
    if 'not_initialized' in existing_snippet_contexts:
        existing_snippet_contexts.clear()
        discover_snippet_contexts()

    if editor.lang not in existing_snippet_contexts:
        return

    contexts = [editor.lang]
    for ctx in contexts:
        if ctx not in loaded_snippets:
            load_snippets_for(ctx)

    editor.view.connect('key-press-event', on_view_key_press_event,
        contexts, weakref.ref(editor))

    editor.buffer.connect_after('changed', on_buffer_changed)

def load_snippets_for(ctx):
    snippets = parse_snippets_from(existing_snippet_contexts[ctx])
    loaded_snippets[ctx] = snippets
    snippet_names = [s.snippet for s in snippets.values()]
    for name in snippet_names:
        snippets_match_hash.setdefault(ctx, {}).setdefault(len(name), {})[name] = True

    completion_providers[ctx] = SnippetsCompletionProvider(ctx)

def discover_snippet_contexts():
    dirs_to_scan = [os.path.join(os.path.dirname(__file__), 'snippets'),
        os.path.join(os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config')),
            'snaked', 'snippets')
    ]

    for d in dirs_to_scan:
        if os.path.exists(d):
            for name in os.listdir(d):
                path = os.path.join(d, name)
                nm, ext = os.path.splitext(name)
                if ext == '.snippets' and os.path.isfile(path):
                    existing_snippet_contexts[nm] = path

def get_match(iter, ctx):
    names = snippets_match_hash.get(ctx, {})
    if not names:
        return None

    for cnt in sorted(names, reverse=True):
        end = iter.copy()
        end.backward_chars(cnt)

        match = end.get_slice(iter)
        if match in names[cnt]:
            return match

    return None

def get_iter_at_cursor(buffer):
    return buffer.get_iter_at_mark(buffer.get_insert())

def on_view_key_press_event(view, event, contexts, editor_ref):
    if event.keyval == gtk.keysyms.Tab:
        buffer = view.get_buffer()
        cursor = get_iter_at_cursor(buffer)

        matches = {}
        for ctx in contexts:
            match = get_match(cursor, ctx)
            if match:
                matches[ctx] = find_all_snippets(ctx, match)

        if matches:
            return expand_snippet(view, matches)

        if buffer in stop_managers:
            sm = stop_managers[buffer]
            if sm.cursor_in_snippet_range(cursor):
                return sm.goto_next_stop(editor_ref())
            else:
                del stop_managers[buffer]

    elif event.keyval == gtk.keysyms.ISO_Left_Tab:
        buffer = view.get_buffer()
        cursor = get_iter_at_cursor(buffer)

        if buffer in stop_managers:
            sm = stop_managers[buffer]
            if sm.cursor_in_snippet_range(cursor):
                return sm.goto_next_stop(editor_ref(), True)
            else:
                del stop_managers[buffer]

    return False

def on_buffer_changed(buffer):
    if buffer in stop_managers:
        cursor = get_iter_at_cursor(buffer)
        sm = stop_managers[buffer]
        if sm.cursor_in_snippet_range(cursor):
            if sm.snippet_collapsed():
                del stop_managers[buffer]
            else:
                idle(sm.replace_inserts)
        else:
            del stop_managers[buffer]

def find_all_snippets(ctx, match):
    return [s for s in loaded_snippets[ctx].values() if s.snippet == match]

def expand_snippet(view, matches):
    if not matches:
        return False
    elif len(matches) == 1:
        snippets = matches.values()[0]
        if not snippets:
            return False

        if len(snippets) == 1:
            insert_snippet(view, get_iter_at_cursor(view.get_buffer()), snippets[0])
            return True

    show_proposals(view, get_iter_at_cursor(view.get_buffer()), matches.keys())
    return True

match_ws = re.compile(u'(?u)^[ \t]*')
def get_whitespace(start):
    match = match_ws.search(line_text(start))
    if match:
        return match.group(0)
    else:
        return u''

def line_text(iter):
    if not iter.starts_line():
        iter = iter.copy()
        iter.set_line(iter.get_line())

    end = iter.copy()
    if not end.ends_line():
        end.forward_to_line_end()

    return iter.get_text(end)

def insert_snippet(view, iter, snippet):
    buffer = view.get_buffer()

    expand_tabs = view.get_insert_spaces_instead_of_tabs()
    tab_width = view.get_tab_width()
    indent = unicode(get_whitespace(iter))

    buffer.begin_user_action()
    start = iter.copy()
    start.backward_chars(len(snippet.snippet))
    buffer.delete(start, iter)

    offset = get_iter_at_cursor(buffer).get_offset()

    body, stop_offsets, insert_offsets = snippet.get_body_and_offsets(
        indent, expand_tabs, tab_width)

    buffer.insert_at_cursor(body)
    buffer.end_user_action()

    stop_managers[buffer] = StopManager(buffer, offset, stop_offsets, insert_offsets)

def show_proposals(view, iter, contexts):
    completion = view.get_completion()
    completion_context = completion.create_context(iter)
    completion.show([completion_providers[c] for c in contexts], completion_context)


class StopManager(object):
    def __init__(self, buffer, offset, stop_offsets, insert_offsets):
        self.buffer = buffer

        self.start_mark = buffer.create_mark(None, buffer.get_iter_at_offset(offset), True)
        self.end_mark = buffer.create_mark(None, get_iter_at_cursor(buffer))

        self.stop_marks = {}
        for i in sorted(stop_offsets):
            s, e = stop_offsets[i]
            s = buffer.create_mark(None, buffer.get_iter_at_offset(offset + s), True)
            e = buffer.create_mark(None, buffer.get_iter_at_offset(offset + e))
            self.stop_marks[i] = s, e

        self.insert_marks = {}
        for i in sorted(insert_offsets):
            s, e = insert_offsets[i]
            s = buffer.create_mark(None, buffer.get_iter_at_offset(offset + s), True)
            e = buffer.create_mark(None, buffer.get_iter_at_offset(offset + e))
            self.insert_marks[i] = s, e

        try:
            self.goto_stop(min(self.stop_marks))
        except ValueError:
            pass

    def goto_stop(self, idx):
        self.buffer.select_range(*reversed(self.get_iter_pair(*self.stop_marks[idx])))

    def get_iter_pair(self, start_mark, end_mark):
        return (self.buffer.get_iter_at_mark(start_mark),
            self.buffer.get_iter_at_mark(end_mark))

    def cursor_in_snippet_range(self, cursor):
        return self.in_range(cursor, *self.get_iter_pair(self.start_mark, self.end_mark))

    def snippet_collapsed(self):
        s, e = self.get_iter_pair(self.start_mark, self.end_mark)
        return s.equal(e)

    def in_range(self, cursor, start, end):
        return cursor.in_range(start, end) or cursor.equal(end)

    def get_current_stop_idx(self, cursor):
        for i, (s, e) in self.stop_marks.iteritems():
            if self.in_range(cursor, *self.get_iter_pair(s, e)):
                return i

        return None

    def goto_next_stop(self, editor, back=False):
        if self.buffer.get_has_selection():
            cursor = self.buffer.get_selection_bounds()[1]
        else:
            cursor = get_iter_at_cursor(self.buffer)

        idx = self.get_current_stop_idx(cursor)
        if idx is not None:
            try:
                if back:
                    idx = max(i for i in self.stop_marks if i < idx)
                else:
                    idx = min(i for i in self.stop_marks if i > idx)
            except ValueError:
                if back:
                    self.buffer.place_cursor(self.buffer.get_iter_at_mark(self.start_mark))
                else:
                    self.buffer.place_cursor(self.buffer.get_iter_at_mark(self.end_mark))

                self.remove(editor)
                return True

            self.goto_stop(idx)
            return True

        return False

    def replace_inserts(self):
        cursor = get_iter_at_cursor(self.buffer)
        if not cursor.equal(self.buffer.get_iter_at_mark(self.end_mark)):
            idx = self.get_current_stop_idx(cursor)
            if idx is not None:
                if idx in self.insert_marks:
                    txt = self.buffer.get_text(*self.get_iter_pair(*self.stop_marks[idx]))
                    s, e = self.insert_marks[idx]
                    self.buffer.handler_block_by_func(on_buffer_changed)
                    self.buffer.begin_user_action()
                    self.buffer.delete(*self.get_iter_pair(s, e))
                    self.buffer.insert(self.buffer.get_iter_at_mark(s), txt)
                    self.buffer.end_user_action()
                    self.buffer.handler_unblock_by_func(on_buffer_changed)

                return

        self.remove()

    def remove(self, editor=None):
        if editor:
            editor.message('Snippet was completed')

        try:
            del stop_managers[self.buffer]
        except KeyError:
            pass


class SnippetProposal(gobject.GObject, CompletionProposal):
    def __init__(self, snippet):
        gobject.GObject.__init__(self)
        self.snippet = snippet

    def do_get_label(self):
        return self.snippet.snippet + (' ' + self.snippet.variant) if self.snippet.variant else ''

    def do_get_text(self):
        return self.snippet.snippet + (' ' + self.snippet.variant) if self.snippet.variant else ''

    def do_get_info(self):
        return self.snippet.comment


class SnippetsCompletionProvider(gobject.GObject, CompletionProvider):
    def __init__(self, ctx):
        gobject.GObject.__init__(self)
        self.ctx = ctx
        self.last_view = None

    def do_get_name(self):
        return '%s snippets' % self.ctx

    def do_get_priority(self):
        return 2

    def do_set_priority(self):
        pass

    def do_get_activation(self):
        return COMPLETION_ACTIVATION_USER_REQUESTED

    def do_populate(self, context):
        match = get_match(context.get_iter(), self.ctx)

        snippets = [s for s in loaded_snippets[self.ctx].values() if s.snippet == match]
        if snippets:
            context.add_proposals(self, [SnippetProposal(s) for s in snippets], True)
            self.last_view = weakref.ref(context.props.completion.props.view)
        else:
            context.add_proposals(self, [], True)

    def do_activate_proposal(self, proposal, iter):
        insert_snippet(self.last_view(), iter, proposal.snippet)
        return True

gobject.type_register(SnippetsCompletionProvider)
gobject.type_register(SnippetProposal)
