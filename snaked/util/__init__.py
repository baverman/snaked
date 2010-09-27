import os
from os.path import join, dirname, realpath, abspath, exists

import gobject
import gtk

from gsignals.signals import Handler
from gsignals import weak_connect

def idle_callback(callable, args):
    args, kwargs = args
    callable(*args, **kwargs)
    return False

def idle(callable, *args, **kwargs):
    return gobject.idle_add(idle_callback, callable, (args, kwargs))

def save_file(filename, data, encoding):
    tmpfilename = realpath(filename) + '.bak'
    
    f = open(tmpfilename, 'w')
    f.write(data.encode(encoding))
    f.close()
    
    os.rename(tmpfilename, filename)

def connect(sender, signal, obj, attr, idle=False, after=False):
    return Handler(weak_connect(
        sender, signal, obj, attr, idle=idle, after=after), sender, None, None)

def join_to_file_dir(filename, *args):
    return join(dirname(filename), *args)

def get_project_root(filename):
    path = dirname(abspath(filename))
    magic_pathes = ['.git', '.hg', '.bzr', '.ropeproject', '.snaked_project']
    
    while True:
        if any(exists(join(path, p)) for p in magic_pathes):
            return path
    
        parent = dirname(path)
        if parent == path:
            return None
    
        path = parent
    
def open_mime(filename):
    import subprocess
    subprocess.Popen(['/usr/bin/env', 'xdg-open', filename]).poll()

    
class BuilderAware(object):
    def __init__(self, glade_file):
        self.gtk_builder = gtk.Builder()
        self.gtk_builder.add_from_file(glade_file)
        self.gtk_builder.connect_signals(self)
    
    def __getattr__(self, name):
        obj = self.gtk_builder.get_object(name)
        if not obj:
            raise AttributeError()
            
        setattr(self, name, obj)
        return obj
