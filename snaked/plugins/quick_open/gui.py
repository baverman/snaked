from snaked.util import join_to_file_dir, BuilderAware
from snaked.core.shortcuts import ShortcutActivator

class QuickOpenDialog(BuilderAware):
    def __init__(self):
        super(QuickOpenDialog, self).__init__(join_to_file_dir(__file__, 'gui.glade'))
        self.shortcuts = ShortcutActivator(self.window)
        self.shortcuts.bind('Escape', self.hide)
        
    def show(self, editor):
        self.window.set_transient_for(editor.window)
        self.window.show()
    
    def hide(self):
        self.window.hide()
        
    def on_delete_event(self, *args):
        self.hide()
        return True
