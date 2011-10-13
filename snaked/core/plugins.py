import sys

from uxie.utils import join_to_data_dir, idle

from .prefs import ListSettings

default_enabled_plugins = ['save_positions', 'edit_and_select',
    'python', 'complete_words', 'hash_comment', 'python_flakes', 'goto_line',
    'goto_dir', 'search']

import snaked.plugins
snaked.plugins.__path__.insert(0, join_to_data_dir('snaked', 'plugins'))

enabled_plugins_prefs = ListSettings('enabled-plugins.db')

def get_package(name):
    try:
        return sys.modules[name]
    except KeyError:
        __import__(name)
        return sys.modules[name]

def get_plugin(name):
    package_name = 'snaked.plugins.' + name
    return get_package(package_name)

def init_plugin(name, manager):
    try:
        p = get_plugin(name)
    except:
        import traceback
        traceback.print_exc()
    else:
        manager.add_plugin(p)

def get_available_plugins():
        return ListSettings('enabled-plugins.db')

def init_plugins(plugin_manager):
    #enabled_plugins = enabled_plugins_prefs.load() or default_enabled_plugins
    for name in ['complete_words', 'edit_and_select', 'goto_line', 'goto_dir', 'hash_comment', 'save_positions', 'search', 'snippets', 'spell', 'external_tools', 'python']:
        idle(init_plugin, name, plugin_manager)

def show_plugins_prefs(self, editor):
    from snaked.core.gui.plugin_prefs import PluginDialog
    dialog = PluginDialog()
    editor.request_transient_for.emit(dialog.window)

    def set_plugin_list(plugin_list):
        self.enabled_plugins = plugin_list
        self.save_enabled_plugins()
        editor.message('Enabled plugins list saved')
        self.unload_unnecessary_plugins()
        editor.plugins_changed.emit()

    dialog.show(self.enabled_plugins, set_plugin_list)
