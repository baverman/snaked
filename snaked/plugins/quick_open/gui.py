import os.path

from snaked.util import join_to_file_dir, BuilderAware
from snaked.core.shortcuts import ShortcutActivator

class QuickOpenDialog(BuilderAware):
    def __init__(self):
        super(QuickOpenDialog, self).__init__(join_to_file_dir(__file__, 'gui.glade'))
        self.shortcuts = ShortcutActivator(self.window)
        self.shortcuts.bind('Escape', self.hide)
        self.shortcuts.bind('<alt>Up', self.project_up)
        self.shortcuts.bind('<alt>Down', self.project_down)
        
    def show(self, editor):
        root = editor.project_root
        if not root:
            root = os.path.dirname(editor.uri)
            
        self.add_project_root(root)

        self.search_entry.grab_focus()
        
        self.window.set_transient_for(editor.window)
        self.window.show()
    
    def add_project_root(self, root):
        for i, r in enumerate(self.projectlist):
            if r[0] == root:
                self.projects_cbox.set_active(i)
                return
                    
        self.projectlist.append((root,))
        self.projects_cbox.set_active(len(self.projectlist) - 1)
    
    def hide(self):
        self.window.hide()
        
    def on_delete_event(self, *args):
        self.hide()
        return True
    
    def project_up(self):
        pass
        
    def project_down(self):
        pass
