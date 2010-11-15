import os.path

import gtk, gobject

from gtksourceview2 import CompletionProvider, CompletionProposal
from gtksourceview2 import COMPLETION_ACTIVATION_USER_REQUESTED

from .parser import parse_snippets_from

loaded_snippets = {}
existing_snippet_contexts = {'not_initialized':True}
snippets_match_hash = {}
completion_providers = {}

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
            
        editor.view.get_completion().add_provider(completion_providers[ctx])

    editor.view.connect('key-press-event', on_view_key_press_event, contexts)

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

def get_matches(iter, ctx):
    names = snippets_match_hash.get(ctx, {})
    if not names:
        return []
    
    matches = []
    for cnt in sorted(names, reverse=True):
        end = iter.copy()
        end.backward_chars(cnt)
        
        match = end.get_slice(iter)
        if match in names[cnt]:
            matches.append(match)        
    
    return matches

def get_iter_at_cursor(buffer):
    return buffer.get_iter_at_mark(buffer.get_insert())

def on_view_key_press_event(view, event, contexts):
    if event.keyval != gtk.keysyms.Tab:
        return False

    matches = []
    for ctx in contexts:
        matches.extend(get_matches(get_iter_at_cursor(view.get_buffer()), ctx))

    return expand_snippet(view, contexts, matches)    

def find_all_snippets(contexts, match):
    result = []
    for ctx in contexts:
        result.extend(s for s in loaded_snippets[ctx].values() if s.snippet == match)
        
    return result
    
def expand_snippet(view, contexts, matches):
    if not matches:
        return False
    elif len(matches) == 1:
        snippets = find_all_snippets(contexts, matches[0])
        if not snippets:
            return False
    
        if len(snippets) == 1:
            insert_snippet(view, get_iter_at_cursor(view.get_buffer()), snippets[0])
            return True

    show_proposals(view, get_iter_at_cursor(view.get_buffer()), contexts)
    return True

def insert_snippet(view, iter, snippet):
    buffer = view.get_buffer()
    buffer.begin_user_action()
    buffer.insert_at_cursor(snippet.get_body_and_offsets()[0])
    buffer.end_user_action()
    
def show_proposals(view, iter, contexts):
    completion = view.get_completion()
    completion_context = completion.create_context(iter)
    completion.show([completion_providers[c] for c in contexts], completion_context)

    
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

    def do_get_name(self):
        return '%s snippets' % self.ctx

    def do_get_priority(self):
        return 2

    def do_set_priority(self):
        pass

    def do_get_activation(self):
        return COMPLETION_ACTIVATION_USER_REQUESTED

    def do_populate(self, context):
        matches = get_matches(context.get_iter(), self.ctx)
        
        snippets = [s for s in loaded_snippets[self.ctx].values() if s.snippet in matches]
        if snippets:
            context.add_proposals(self, [SnippetProposal(s) for s in snippets], True)
        else:
            context.add_proposals(self, [], True)
            
gobject.type_register(SnippetsCompletionProvider)
gobject.type_register(SnippetProposal)
