import os.path, sys

import gtk
from uxie.utils import idle

from snaked.util import lazy_property
from snaked.signals import connect_external, connect_all
from snaked.core.completer import add_completion_provider, attach_completer

from .utils import get_env

configured_projects = {}

class Plugin(object):
    def __init__(self, editor):
        self.editor = editor
        idle(connect_all, self, view=editor.view)
        idle(self.init_completion)

    def init_completion(self):
        provider = self.completion_provider

        if not hasattr(self.editor.buffer, 'python_completion_added'):
            add_completion_provider(self.editor.buffer, provider, 100)
            self.editor.buffer.python_completion_added = True

        attach_completer(self.editor.view)

    @property
    def env(self):
        return get_env(self.editor.conf)

    @lazy_property
    def project_path(self):
        root = getattr(self.editor, 'ropeproject_root', self.editor.project_root)

        if not root:
            root = os.path.dirname(self.editor.uri)

        if root not in configured_projects:
            conf = self.editor.conf['PYTHON_SUPP_CONFIG']
            if conf:
                self.env.configure_project(root, conf)

            configured_projects[root] = True

        return root

    @lazy_property
    def completion_provider(self):
        import complete
        return complete.RopeCompletionProvider(self)

    def get_source_and_offset(self):
        offset = self.editor.cursor.get_offset()
        source = self.editor.text

        if not isinstance(source, unicode):
            source = source.decode('utf8')

        return source, offset

    def goto_definition(self):
        source, offset = self.get_source_and_offset()
        try:
            line, fname = self.env.get_location(self.project_path, source, offset, self.editor.uri)
        except Exception, e:
            import traceback
            traceback.print_exc()
            self.editor.message(str(e), 'error', 5000)
            return

        if fname == self.editor.uri:
            fname = None

        if fname:
            editor = self.editor.window.open_or_activate(fname, line - 1)
            editor.supplement_project_root = self.project_path
        else:
            if line:
                self.editor.add_spot()
                self.editor.goto_line(line)
            else:
                self.editor.message("Unknown definition", 'warn')

    @connect_external('view', 'key-press-event')
    def on_textview_key_press_event(self, sender, event):
        if event.keyval != gtk.keysyms.Return:
            return False

        cursor = self.editor.cursor
        line_start = cursor.copy()
        line_start.set_line(line_start.get_line())

        text = line_start.get_text(cursor).strip()
        if text and text[-1] == ':':
            end = line_start.copy()
            end.forward_word_end()
            end.backward_word_start()
            ws = line_start.get_text(end)

            if self.editor.view.get_insert_spaces_instead_of_tabs():
                tab = u' ' * self.editor.view.get_tab_width()
            else:
                tab = u'\t'

            self.editor.buffer.begin_user_action()
            self.editor.buffer.insert(cursor, u'\n' + ws + tab)
            self.editor.buffer.end_user_action()

            idle(self.editor.view.scroll_mark_onscreen, self.editor.buffer.get_insert())

            return True

        return False

    @connect_external('view', 'backspace')
    def on_textview_backspace(self, *args):
        cursor = self.editor.cursor

        if cursor.starts_line():
            return False

        start = cursor.copy()
        start.set_line(start.get_line())

        text = start.get_text(cursor)

        if text.strip():
            return False

        delete_from = cursor.copy()
        if text[-1] == u'\t':
            delete_from.backward_char()
        else:
            delete_from.backward_chars(self.editor.view.get_tab_width() - 1)

        if delete_from.get_line() != start.get_line():
            delete_from = start

        if delete_from.equal(start):
            delete_from.forward_char()

        self.editor.buffer.begin_user_action()
        self.editor.buffer.delete(delete_from, cursor)
        self.editor.buffer.end_user_action()

        return True

    def show_calltips(self):
        source, offset = self.get_source_and_offset()
        try:
            result = self.env.get_docstring(self.project_path, source, offset, self.editor.uri)
        except Exception, e:
            import traceback
            traceback.print_exc()
            self.editor.message(str(e), 'error', 5000)
            return

        if not result:
            self.editor.message("Can't get docstring", 'warn')
            return

        sig, docstring = result
        if sig:
            docstring = sig + '\n\n' + ( docstring if docstring is not None else '' )

        if docstring:
            self.editor.message(docstring, 'info', 20000)
        else:
            self.editor.message('Info not found', 'warn', 3000)

    def get_scope(self):
        source, _ = self.get_source_and_offset()
        return self.editor.uri, self.env.get_scope(self.project_path,
            source, self.editor.cursor.get_line() + 1, self.editor.uri, False)
