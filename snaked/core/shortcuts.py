import gtk

class ShortcutManager(object):
    def __init__(self):
        self.shortcuts = {}
        
    def add(self, name, accel, category, desc):
        self.shortcuts[name] = Shortcut(name, accel, category, desc)

    def bind(self, activator, name, callback):
        activator.bind(self.shortcuts[name].accel, callback)
                

class Shortcut(object):
    def __init__(self, name, accel, category, desc):
        self.name = name
        self.accel = accel
        self.category = category
        self.desc = desc


class ShortcutActivator(object):
    def __init__(self, window):
        self.window = window
        self.accel_group = gtk.AccelGroup()
        self.window.add_accel_group(self.accel_group)
        
        self.shortcuts = {}
        
    def bind(self, accel, callback):
        key, modifier = gtk.accelerator_parse(accel)
        self.shortcuts[(key, modifier)] = callback
        
        self.accel_group.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.activate)
        
    def activate(self, group, window, key, modifier):
        self.shortcuts[(key, modifier)]()
        return True
