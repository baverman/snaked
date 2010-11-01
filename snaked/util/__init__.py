import os
import shutil
from os.path import join, dirname, realpath, abspath, exists

import gobject
import gtk

from snaked.signals.signals import Handler
from snaked.signals import weak_connect

def idle_callback(callable, args):
    args, kwargs = args
    callable(*args, **kwargs)
    return False

def idle(callable, *args, **kwargs):
    return gobject.idle_add(idle_callback, callable, (args, kwargs))

def save_file(filename, data, encoding):
    tmpfilename = realpath(filename) + '.bak'

    try:
        f = open(tmpfilename, 'w')
    except IOError:
        dname = dirname(tmpfilename)
        if not exists(dname):
            os.makedirs(dname, mode=0755)
            f = open(tmpfilename, 'w')
        else:
            raise
                    
    f.write(data.encode(encoding))
    f.close()
    
    if exists(filename):
        shutil.copymode(filename, tmpfilename)
    
    os.rename(tmpfilename, filename)

def connect(sender, signal, obj, attr, idle=False, after=False):
    return Handler(weak_connect(
        sender, signal, obj, attr, idle=idle, after=after), sender)

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


def refresh_gui():
    while gtk.events_pending():
        gtk.main_iteration_do(block=False)

def single_ref(func):
    real_name = '__' + func.__name__
    holder_name = func.__name__ + '_holder'
    
    def inner(self):
        try:
            return getattr(self, real_name)
        except AttributeError:
            pass
            
        cls = self.__class__
        if not hasattr(cls, holder_name) or not getattr(cls, holder_name)():
            import weakref
            var = func(self)
            setattr(cls, holder_name, weakref.ref(var))
        
        setattr(self, real_name, getattr(cls, holder_name)())
        return getattr(self, real_name)
        
    return property(inner)

def lazy_property(func):
    real_name = '__' + func.__name__
    
    def inner(self):
        try:
            return getattr(self, real_name)
        except AttributeError:
            pass
        
        var = func(self)
        setattr(self, real_name, var)
        return var
        
    return property(inner)

def set_activate_the_one_item(entry, treeview):
    def activate(*args):
        if len(treeview.get_model()) == 1:
            treeview.set_cursor((0,))
            treeview.row_activated((0,), treeview.get_column(0))
        
    entry.connect('activate', activate)


class BuilderAware(object):
    def __init__(self, glade_file):
        self.gtk_builder = gtk.Builder()
        self.gtk_builder.add_from_file(glade_file)
        self.gtk_builder.connect_signals(self)
    
    def __getattr__(self, name):
        obj = self.gtk_builder.get_object(name)
        if not obj:
            raise AttributeError('Builder have no %s object' % name)
            
        setattr(self, name, obj)
        return obj
