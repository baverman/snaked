import os.path, sys

import gtk

from snaked.signals import connect_external, connect_all
from snaked.util import idle, lazy_property

environments = {}
configured_projects = {}

class Plugin(object):
    def __init__(self, editor):
        self.editor = editor
        idle(connect_all, self, view=editor.view)
        idle(self.init_completion)

    def init_completion(self):
        provider = self.completion_provider
        completion = self.editor.view.get_completion()
        completion.add_provider(provider)

    @property
    def env(self):
        executable = self.editor.snaked_conf['PYTHON_EXECUTABLE']
        if executable == 'default':
            executable = sys.executable

        env = self.editor.snaked_conf['PYTHON_EXECUTABLE_ENV']

        try:
            env = environments[executable]
        except KeyError:
            import supplement.remote
            env = environments[executable] = supplement.remote.Environment(executable, env)

        return env

    @lazy_property
    def project_path(self):
        root = getattr(self.editor, 'ropeproject_root', self.editor.project_root)

        if not root:
            self.editor.message('Supp warning: there is no project. Assist was degraded', 3000)
            root = os.path.dirname(self.editor.uri)

        if root not in configured_projects:
            conf = self.editor.snaked_conf['PYTHON_SUPP_CONFIG']
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
            self.editor.message(str(e), 5000)
            return

        if fname == self.editor.uri:
            fname = None

        if fname:
            editor = self.editor.open_file(fname, line - 1)
            editor.supplement_project_root = self.project_path
        else:
            if line:
                self.editor.add_spot()
                self.editor.goto_line(line)
            else:
                self.editor.message("Unknown definition")

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
            sig, docstring = self.env.get_docstring(self.project_path, source, offset, self.editor.uri)
        except Exception, e:
            import traceback
            traceback.print_exc()
            self.editor.message(str(e), 5000)
            return

        if sig:
            docstring = sig + '\n\n' + ( docstring if docstring is not None else '' )

        if docstring:
            self.editor.message(docstring, 20000)
        else:
            self.editor.message('Info not found', 3000)

    def get_scope(self):
        source, _ = self.get_source_and_offset()
        return self.editor.uri, self.env.get_scope(self.project_path,
            source, self.editor.cursor.get_line() + 1, self.editor.uri, False)
