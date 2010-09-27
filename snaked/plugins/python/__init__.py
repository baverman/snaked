from gsignals import connect_all

from snaked.util import idle
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
    
    @EditorSignals.update_title
    def update_title(self, sender):
        if self.editor.uri.endswith('.py'):
            return get_python_title(self.editor.uri)
        
        return None