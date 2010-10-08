import gtk
import os.path

from snaked.core.prefs import get_settings_path

registered_shortcuts = {}
names_by_key = {}
default_shortcuts = {}

def get_path_by_name(name):
    return "<Snaked-Editor>/%s/%s" % (registered_shortcuts[name][0], name)

def get_registered_shortcuts():
    result = []
    
    def func(path, key, mod, changed):
        result.append((path, key, mod))
        
    gtk.accel_map_foreach_unfiltered(func)
    
    return result
    
def refresh_names_by_key():
    for path, key, mod in get_registered_shortcuts():
        names_by_key[(key, mod)] = path

def get_path_by_key(key, mod):
    try:
        return names_by_key[(key, mod)]
    except KeyError:
        refresh_names_by_key()
        return names_by_key[(key, mod)]

def register_shortcut(name, accel, category, desc):
    registered_shortcuts[name] = category, desc
    key, modifier = gtk.accelerator_parse(accel)
    path = get_path_by_name(name)
    default_shortcuts[path] = (key, modifier)
    gtk.accel_map_add_entry(path, key, modifier)    
    
    return path

def save_shortcuts():
    gtk.accel_map_save(get_settings_path('keys.conf'))
    
def load_shortcuts():
    config = get_settings_path('keys.conf')
    if os.path.exists(config):
        gtk.accel_map_load(config)

class Shortcut(object):
    def __init__(self, name, accel, category, desc):
        self.name = name
        self.accel = accel
        self.category = category
        self.desc = desc

    @property
    def keymod(self):
        try:
            return self.__keymod
        except AttributeError:
            self.__keymod = gtk.accelerator_parse(self.accel)
            return self.__keymod


class ShortcutActivator(object):
    def __init__(self, window):
        self.window = window
        self.accel_group = gtk.AccelGroup()
        self.window.add_accel_group(self.accel_group)
        
        self.shortcuts = {}
        self.pathes = {}
        
    def bind(self, accel, callback, *args):
        key, modifier = gtk.accelerator_parse(accel)
        self.shortcuts[(key, modifier)] = callback, args
        
        self.accel_group.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.activate)
    
    def bind_to_name(self, name, callback, *args):
        path = get_path_by_name(name)
        self.pathes[path] = callback, args
        self.accel_group.connect_by_path(path, self.activate)
    
    def get_callback_and_args(self, *key):
        try:
            return self.shortcuts[key]
        except KeyError:
            return self.pathes[get_path_by_key(*key)]
    
    def activate(self, group, window, key, modifier):
        cb, args = self.get_callback_and_args(key, modifier)
        result = cb(*args)
        return result is None or result


class ContextShortcutActivator(ShortcutActivator):
    def __init__(self, window, context):
        super(ContextShortcutActivator, self).__init__(window)
        self.context = context

    def activate(self, group, window, key, modifier):
        ctx = self.context()
        cb, args = self.get_callback_and_args(key, modifier)
        
        if hasattr(cb, 'provide_key'):
            return cb(key, modifier, *(ctx + args))
        else:
            result = cb(*(ctx + args))
            return result is None or result
