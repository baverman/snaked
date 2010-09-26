import os.path

from snaked.util import join_to_file_dir, BuilderAware
from snaked.core.shortcuts import ShortcutActivator

import settings

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

        self.update_projects(root)

        self.search_entry.grab_focus()
        
        self.window.set_transient_for(editor.window)
        self.window.show()
    
    def update_projects(self, root):
        self.projects_cbox.set_model(None)
        self.projectlist.clear()
        
        index = -1
        for i, r in enumerate(settings.recent_projects):
            if r == root:
                index = i
            self.projectlist.append((r,))
        
        self.projects_cbox.set_model(self.projectlist)
        self.projects_cbox.set_active(index)
    
    def hide(self):
        self.window.hide()
        
    def on_delete_event(self, *args):
        self.hide()
        return True
    
    def project_up(self):
        pass
        
    def project_down(self):
        pass
