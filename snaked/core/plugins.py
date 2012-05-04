import sys

from uxie.utils import join_to_data_dir, idle

from .prefs import ListSettings

import snaked.plugins
snaked.plugins.__path__.insert(0, join_to_data_dir('snaked', 'plugins'))

default_enabled_plugins = ['save_positions', 'edit_and_select',
    'python', 'complete_words', 'hash_comment', 'python_flakes', 'goto_line',
    'search']

enabled_plugins = []

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
    enabled_plugins[:] = enabled_plugins_prefs.load(default_enabled_plugins)
    for name in enabled_plugins:
        idle(init_plugin, name, plugin_manager)

def show_plugins_prefs(window):
    from snaked.core.gui.plugin_prefs import PluginDialog
    dialog = PluginDialog()
    dialog.window.set_transient_for(window)

    def set_plugin_list(plugin_list):
        enabled_plugins_prefs.store(plugin_list)
        plugins_activated = False
        for name in [r for r in plugin_list if r not in enabled_plugins]:
            plugins_activated = True
            enabled_plugins.append(name)
            init_plugin(name, window.manager.plugin_manager)

        window.message('Enabled plugins list saved', 'done', 5000)

        if plugins_activated:
            window.message('Enabled plugins have been activated', 'done', 5000)

        if any(r not in plugin_list for r in enabled_plugins):
            window.message('You should restart snaked to deactivate disabled plugins', 'warn', 5000)

    dialog.show(enabled_plugins_prefs.load(default_enabled_plugins), set_plugin_list)
