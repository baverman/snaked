import os.path
from snaked.util import idle, single_ref

class Plugin(object):
        
    def __init__(self, editor):
        self.editor = editor
        idle(self.register_project)
    
    @staticmethod
    def register_shortcuts(manager):
        manager.add('quick-open', '<ctrl><alt>r', 'File', "Shows quick open dialog")
    
    def init_shortcuts(self, manager):
        manager.bind(self.editor.activator, 'quick-open', self.activate)
    
    @single_ref
    def gui(self):
        import gui
        return gui.QuickOpenDialog()
        
    def activate(self):
        self.gui.show(self.editor)
        
    def register_project(self):
        import settings
        
        root = self.editor.project_root
        if not root:
            root = os.path.dirname(self.editor.uri)
        
        if root not in settings.recent_projects:            
            settings.recent_projects.append(root)                
