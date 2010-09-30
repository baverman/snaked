import os
import sys
from os.path import join, isdir, exists
from .shortcuts import Shortcut
import traceback

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
    return get_package(package_name)


class ShortcutsHolder(object):
    def __init__(self):
        self.shortcuts = []

    def add_shortcut(self, name, accel, category, desc, callback):
        self.shortcuts.append((name, accel, category, desc, callback))


class PluginManager(object):
    def __init__(self):
        self.enabled_plugins = ['quick_open', 'save_positions', 'edit_and_select',
            'python', 'complete_words']

        self.loaded_plugins = {}

        self.plugin_by_keys = {}
        self.shortcuts_by_plugins = {}
        self.binded_shortcuts = {}

    def get_plugin(self, name):
        try:
            return self.loaded_plugins[name]
        except KeyError:
            plugin = get_plugin(name)
            if hasattr(plugin, 'init'):
                holder = ShortcutsHolder()
                plugin.init(holder)
                self.add_shortcuts(plugin, holder)
            self.loaded_plugins[name] = plugin
            return plugin

    def add_shortcuts(self, plugin, holder):
        for name, accel, category, desc, callback in holder.shortcuts:
            shortcut = Shortcut(name, accel, category, desc)
            shortcut.callback = callback

            self.plugin_by_keys[shortcut.keymod] = plugin
            self.shortcuts_by_plugins.setdefault(plugin, []).append(shortcut)

    def bind_shortcuts(self, activator, editor):
        for p in self.plugins_for(editor):
            for s in self.shortcuts_by_plugins.get(p, []):
                try:
                    self.binded_shortcuts[activator][s.name]
                except KeyError:
                    activator.bind(s.accel, s.callback)

    def get_plugin_by_key(self, key, modifier):
        return self.plugin_by_keys.get((key, modifier), None)

    def plugin_is_for_editor(self, plugin, editor):
        return not hasattr(plugin, 'langs') or editor.lang in plugin.langs

    def plugins_for(self, editor):
        for name in self.enabled_plugins:
            plugin = self.get_plugin(name)
            if self.plugin_is_for_editor(plugin, editor):
                yield plugin

    def editor_opened(self, editor):
        for p in self.plugins_for(editor):
            if hasattr(p, 'editor_opened'):
                try:
                    p.editor_opened(editor)
                except:
                    traceback.print_exc()

    def editor_closed(self, editor):
        for p in self.plugins_for(editor):
            if hasattr(p, 'editor_closed'):
                try:
                    p.editor_closed(editor)
                except:
                    traceback.print_exc()

    def quit(self):
        for p in self.loaded_plugins.values():
            if hasattr(p, 'quit'):
                try:
                    p.quit()
                except:
                    traceback.print_exc()
