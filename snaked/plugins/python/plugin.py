import os

import gtk
import gio

from snaked.signals import connect_external, connect_all
from snaked.util import idle, refresh_gui, lazy_property

from .ropehints import FileHintDb

class Plugin(object):
    def __init__(self, editor):
        self.editor = editor
        idle(connect_all, self, view=editor.view)
        idle(self.init_completion)

    def init_completion(self):
        provider = self.completion_provider
        self.editor.view.get_completion().add_provider(provider)
        
    def close(self):
        if hasattr(self, '__project'):
            self.project.close()
            self.hints_monitor.cancel()
    
    def refresh_hints(self, filemonitor, file, other_file, event, db, project):
        if event in (gio.FILE_MONITOR_EVENT_CHANGES_DONE_HINT, gio.FILE_MONITOR_EVENT_CREATED):        
            db.refresh()
            project.pycore.module_cache.forget_all_data()

    @lazy_property
    def project(self):
        if not os.access(self.editor.uri, os.W_OK):
            root = '/tmp'
        else:
            root = self.editor.project_root
        
        if root:
            from rope.base.project import Project
            project = Project(root)
            db = FileHintDb(project)

            self.hints_monitor = gio.File(db.hints_filename).monitor_file()
            self.hints_monitor.connect('changed', self.refresh_hints, db, project)
            
            return project
        else:
            return None           
    
    @lazy_property
    def completion_provider(self):
        import complete
        return complete.RopeCompletionProvider(self)

    def get_rope_resource(self, project, uri=None):
        from rope.base import libutils    
        uri = uri or self.editor.uri
        return libutils.path_to_resource(project, uri)

    def get_source_and_offset(self):
        offset = self.editor.cursor.get_offset()
        source = self.editor.text
        
        if not isinstance(source, unicode):
            source = source.decode('utf8')
        
        return source, offset

    def goto_line(self, editor, line):
        refresh_gui()
        edit = editor.buffer
        iterator = edit.get_iter_at_line(line - 1)
        edit.place_cursor(iterator)
        editor.view.scroll_to_iter(iterator, 0.001, use_align=True, xalign=1.0)
    
    def get_fuzzy_location(self, source, offset):
        from rope.base import worder, exceptions
        
        word_finder = worder.Worder(source, True)
        expression = word_finder.get_primary_at(offset)
        expression = expression.replace('\\\n', ' ').replace('\n', ' ')
        
        names = expression.split('.')
        pyname = None
        try:
            obj = self.project.pycore.get_module(names[0])
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
        project = self.project
        if not project:
            project = getattr(self.editor, 'ropeproject', None)
            if not project:
                self.editor.message("Can't find project path")
                return
        
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
            resource, line = self.get_fuzzy_location(source, offset)
        
        if resource and resource.real_path == current_resource.real_path:
            resource = None
            
        if resource:
            uri = resource.real_path
            editor = self.editor.open_file(uri, line-1)
            editor.ropeproject = project 
        else:
            if line:
                self.goto_line(self.editor, line)
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
            
            if cursor.is_end():
                idle(self.editor.view.scroll_to_iter, cursor, 0.001, use_align=True, xalign=1.0)
            
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
        project = self.project
        if not project:
            project = getattr(self.editor, 'ropeproject', None)
            if not project:
                self.editor.message("Can't find project path")
                return
        
        project.validate()

        current_resource = self.get_rope_resource(project) 
        
        from rope.contrib import codeassist
        from snaked.util.pairs_parser import get_brackets
 
        source, offset = self.get_source_and_offset()
        
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