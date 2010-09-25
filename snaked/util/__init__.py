import gobject
import os, os.path

def idle_callback(callable, args):
    args, kwargs = args
    callable(*args, **kwargs)
    return False

def idle(callable, *args, **kwargs):
    return gobject.idle_add(idle_callback, callable, (args, kwargs))

def save_file(filename, data, encoding):
    tmpfilename = os.path.realpath(filename) + '.bak'
    
    f = open(tmpfilename, 'w')
    f.write(data.encode(encoding))
    f.close()
    
    os.rename(tmpfilename, filename)
