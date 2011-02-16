import os

import weakref
import gtk
import gio

from snaked.signals import connect_external, connect_all, weak_connect
from snaked.util import idle, lazy_property

from .ropehints import CompositeHintProvider

project_managers = weakref.WeakValueDictionary()

class RopeProjectManager(object):
    def __init__(self, project):
        """:type project: rope.base.project.Project()"""
        self.project = project
        self.hints_monitor = None

        if project.ropefolder:
            self.hints_filename = os.path.join(project.ropefolder.real_path, 'ropehints.py')
            self.hints_monitor = gio.File(self.hints_filename).monitor_file()
            weak_connect(self.hints_monitor, 'changed', self, 'on_hints_file_changed')
        else:
            self.hints_filename = None

        self.refresh_hints()

    def refresh_hints(self):
        self.project.pycore.module_cache.forget_all_data()
        self.project.pycore.hintdb = CompositeHintProvider(self.project)

        if self.hints_filename and os.path.exists(self.hints_filename):
            namespace = {}
            execfile(self.hints_filename, namespace)
            if 'init' in namespace:
                try:
                    namespace['init'](self.project.pycore.hintdb)
                except:
                    import traceback
                    traceback.print_exc()

    def on_hints_file_changed(self, filemonitor, file, other_file, event):
        if event in (gio.FILE_MONITOR_EVENT_CHANGES_DONE_HINT, gio.FILE_MONITOR_EVENT_CREATED):
            self.refresh_hints()

    def close(self):
        if self.hints_monitor:
            self.hints_monitor.cancel()
            self.hints_monitor = None
        self.project.close()

    def __del__(self):
        self.close()

class Plugin(object):
    def __init__(self, editor):
        self.editor = editor
        idle(connect_all, self, view=editor.view)
        idle(self.init_completion)

    def init_completion(self):
        provider = self.completion_provider
        completion = self.editor.view.get_completion()
        completion.add_provider(provider)

    @lazy_property
    def project_manager(self):
        root = getattr(self.editor, 'ropeproject_root', self.editor.project_root)
        try:
            return project_managers[root]
        except KeyError:
            pass

        from rope.base.project import Project, NoProject
        from rope.base.fscommands import FileSystemCommands

        if not root:
            self.editor.message('Rope warning: there is no project. Assist was degraded', 3000)
            project = NoProject()
            project.validate = lambda *args: None
            project.root = None
        else:
            if os.access(root, os.W_OK):
                kwargs = {}
            else:
                kwargs = dict(ropefolder=None)

            project = Project(root, fscommands=FileSystemCommands(), **kwargs)

        project.snaked_project_root = root
        pm = RopeProjectManager(project)
        if root:
            project_managers[root] = pm

        return pm

    @lazy_property
    def completion_provider(self):
        import complete
        return complete.RopeCompletionProvider(self)

    def get_rope_resource(self, project, uri=None):
        from rope.base import libutils, exceptions
        uri = uri or self.editor.uri

        if not hasattr(project, 'address'):
            return project.get_file(uri)
        else:
            try:
                return libutils.path_to_resource(project, uri)
            except exceptions.ResourceNotFoundError:
                from rope.base.project import NoProject
                resource = NoProject().get_file(uri)
                resource.read = lambda: ''
                return resource

    def get_source_and_offset(self):
        offset = self.editor.cursor.get_offset()
        source = self.editor.text

        if not isinstance(source, unicode):
            source = source.decode('utf8')

        return source, offset

    def get_fuzzy_location(self, project, source, offset):
        from rope.base import worder, exceptions

        word_finder = worder.Worder(source, True)
        expression = word_finder.get_primary_at(offset)
        expression = expression.replace('\\\n', ' ').replace('\n', ' ')

        names = expression.split('.')
        pyname = None
        try:
            obj = project.pycore.get_module(names[0])
            for n in names[1:]:
                pyname = obj[n]
                obj = pyname.get_object()
        except (exceptions.ModuleNotFoundError, exceptions.AttributeNotFoundError):
            return None, None

        if not pyname:
            try:
                resource = obj._get_init_dot_py()
            except AttributeError:
                resource = obj.get_resource()

            if not resource:
                return None, None
            else:
                return resource, 1
        else:
            resource, line = pyname.get_definition_location()
            if hasattr(resource, 'resource'):
                resource = resource.resource

        return resource, line

    def goto_definition(self):
        project = self.project_manager.project

        project.validate()

        current_resource = self.get_rope_resource(project)

        from rope.contrib import codeassist

        source, offset = self.get_source_and_offset()
        try:
            resource, line = codeassist.get_definition_location(
                project, source, offset,
                resource=current_resource, maxfixes=3)
        except Exception, e:
            import traceback
            traceback.print_exc()
            self.editor.message(str(e), 5000)
            return

        if resource is None and line is None:
            resource, line = self.get_fuzzy_location(project, source, offset)

        if resource and resource.real_path == current_resource.real_path:
            resource = None

        if resource:
            uri = resource.real_path
            editor = self.editor.open_file(uri, line - 1)
            editor.ropeproject_root = project.snaked_project_root
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
        project = self.project_manager.project
        project.validate()

        current_resource = self.get_rope_resource(project)

        from rope.contrib import codeassist
        from snaked.util.pairs_parser import get_brackets

        source, offset = self.get_source_and_offset()

        # make foo.bar.baz( equivalent to foo.bar.baz
        if source[offset-1] in '(.':
            offset -= 1

        brackets = get_brackets(source, offset)
        if brackets:
            br, spos, epos = brackets
            if br == '(':
                offset = spos - 1

        try:
            doc = codeassist.get_doc(project, source, offset, resource=current_resource, maxfixes=3)
        except Exception, e:
            import traceback
            traceback.print_exc()
            self.editor.message(str(e), 5000)
            return

        if doc:
            self.editor.message(doc.strip(), 20000)
        else:
            self.editor.message('Info not found')

    def get_scope(self):
        project = self.project_manager.project
        project.validate()

        resource = self.get_rope_resource(project)
        source, offset = self.get_source_and_offset()

        module = self.project_manager.project.pycore.get_string_module(source, resource, True)
        scope = module.get_scope().get_inner_scope_for_offset(offset)

        return self.get_file_and_scope(scope)

    def get_file_and_scope(self, scope):
        from rope.base.pyobjectsdef import PyModule, PyPackage

        names = []
        while scope:
            obj = scope.pyobject
            if isinstance(obj, (PyModule, PyPackage)):
                if obj.resource:
                    return obj.resource.path, '.'.join(names)
                else:
                    return None, None
            else:
                names.append(obj.get_name())

            scope = scope.parent

        return None, None
