
class Plugin(object):
    
    def __init__(self, editor):
        self.editor = editor
    
    @staticmethod
    def register_shortcuts(manager):
        manager.add('quick-open', '<ctrl><shift>r', 'File', "Shows quick open dialog")
    
    def init_shortcuts(self, manager):
        manager.bind(self.editor.activator, 'quick-open', self.activate)
        
    def activate(self):
        print 'Booooo!'
