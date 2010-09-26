import os.path
from snaked.util import idle

class Plugin(object):
        
    def __init__(self, editor):
        self.editor = editor
        idle(self.register_project)
    
    @staticmethod
    def register_shortcuts(manager):
        manager.add('quick-open', '<ctrl><alt>r', 'File', "Shows quick open dialog")
    
    def init_shortcuts(self, manager):
        manager.bind(self.editor.activator, 'quick-open', self.activate)
    
    @property
    def gui(self):
        try:
            return self.__gui
        except AttributeError:
            pass
        
        if not hasattr(Plugin, 'gui_holder') or not Plugin.gui_holder():
            import gui, weakref
            var = gui.QuickOpenDialog()
            Plugin.gui_holder = weakref.ref(var)
        
        self.__gui = Plugin.gui_holder()
        return self.__gui
        
    def activate(self):
        self.gui.show(self.editor)
        
    def register_project(self):
        import settings
        
        root = self.editor.project_root
        if not root:
            root = os.path.dirname(self.editor.uri)
        
        if root not in settings.recent_projects:            
            settings.recent_projects.append(root)                
