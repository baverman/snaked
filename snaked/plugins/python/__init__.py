from gsignals import connect_all

from snaked.util import idle, refresh_gui
from snaked.core.signals import EditorSignals

def get_python_title(uri):
    from os.path import dirname, basename, exists, join
    
    title = basename(uri)
    packages = []
    while True:
        path = dirname(uri)
        if path == uri:
            break
        
        uri = path
        
        if exists(join(uri, '__init__.py')):
            packages.append(basename(uri))
        else:
            break
            
    if packages:
        if title != '__init__.py':
            packages.insert(0, title.partition('.py')[0])
            
        return '.'.join(reversed(packages))
    else:
        return None

class Plugin(object):
    def __init__(self, editor):
        self.editor = editor
        idle(connect_all, self, self.editor.signals)
        idle(self.editor.update_title) 
    
    @staticmethod
    def register_shortcuts(manager):
        manager.add('python-goto-definition', 'F3', 'Python', 'Navigates to python definition')
    
    def init_shortcuts(self, manager):
        manager.bind(self.editor.activator, 'python-goto-definition', self.goto_definition)
        
    @EditorSignals.update_title
    def update_title(self, sender):
        if self.editor.uri.endswith('.py'):
            return get_python_title(self.editor.uri)
        
        return None

    @property
    def project(self):
        try:
            return self.__project
        except AttributeError:
            root = self.editor.project_root
            if root:
                from rope.base.project import Project
                self.__project = Project(root)
            else:
                self.__project = None
                
            return self.__project

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

    def goto_definition(self):
        project = self.project
        if not project:
            project = getattr(self.editor, 'ropeproject', None)
            if not project:
                print "Can't find project path"
                return
        
        project.validate()
                 
        current_resource = self.get_rope_resource(project) 
        
        from rope.contrib import codeassist

        try:
            resource, line = codeassist.get_definition_location(
                project, *self.get_source_and_offset(),
                resource=current_resource)
        except Exception, e:
            import traceback
            traceback.print_exc()
            return
        
        if resource and resource.real_path == current_resource.real_path:
            resource = None
            
        if resource:
            uri = resource.real_path
            editor = self.editor.request_to_open_file(uri)
            editor.ropeproject = project 
            self.goto_line(editor, line)
        else:
            if line:
                self.goto_line(self.editor, line)
            else:
                print "Unknown definition"
