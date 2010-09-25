import gtk

class ShortcutManager(object):
    def __init__(self, window):
        self.window = window
        self.accel_group = gtk.AccelGroup()
        self.window.add_accel_group(self.accel_group)
        
        self.shortcuts = {}
        
    def add_shortcut(self, name, accel, category, desc, callback):
        key, modifier = gtk.accelerator_parse(accel)
        self.shortcuts[(key, modifier)] = callback
        
        self.accel_group.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.activate)
        
    def activate(self, group, window, key, modifier):
        self.shortcuts[(key, modifier)]()
        return True
