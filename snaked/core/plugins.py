import os
import sys
from os.path import join, isdir, exists

def discover_plugins():
    import snaked.plugins
    result = {}
    for p in snaked.plugins.__path__:
        print p
        for n in os.listdir(p):         
            if isdir(join(p, n)) and exists(join(p, n, '__init__.py')):
                result[n] = True
                
    return result.keys()

def get_package(name):
    try:
        return sys.modules[name]
    except KeyError:
        __import__(name)
        return sys.modules[name]
        
def get_plugin(plugin):
    package_name = 'snaked.plugins.' + plugin
    return get_package(package_name).Plugin


class PluginManager(object):
    def __init__(self):
        self.enabled_plugins = ['quick_open', 'python', 'complete_words', 'edit_and_select']
        self.registered_plugins = {}
        
    def get_plugin(self, name):
        try:
            return self.registered_plugins[name]
        except KeyError:
            self.registered_plugins[name] = get_plugin(name)
            return self.registered_plugins[name]
    
    @property
    def plugins(self):
        for name in self.enabled_plugins:
            yield self.get_plugin(name)
    
    def register_shortcuts(self, manager):
        for p in self.plugins:
            if hasattr(p, 'register_shortcuts'):
                p.register_shortcuts(manager)
