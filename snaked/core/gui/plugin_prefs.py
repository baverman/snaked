import os
from os.path import join, isdir, exists

from glib import markup_escape_text

from uxie.utils import join_to_file_dir, idle
from uxie.misc import BuilderAware

from snaked.core.plugins import get_plugin

def discover_plugins():
    import snaked.plugins
    result = {}
    for p in snaked.plugins.__path__:
        try:
            for n in os.listdir(p):
                if isdir(join(p, n)) and exists(join(p, n, '__init__.py')):
                    result[n] = True
        except OSError:
            pass

    return result.keys()


class PluginDialog(BuilderAware):
    def __init__(self):
        BuilderAware.__init__(self, join_to_file_dir(__file__, 'plugin_prefs.glade'))

        from snaked.core.manager import keymap
        self.activator = keymap.get_activator(self.window)
        self.activator.bind('any', 'escape', None, self.hide)


    def show(self, enabled_plugins, callback):
        self.callback = callback
        self.fill_plugin_list(enabled_plugins)
        self.window.present()

    def hide(self):
        enabled_plugins = [p[1] for p in self.plugins if p[0]]
        self.callback(enabled_plugins)
        self.window.destroy()

    def on_delete_event(self, *args):
        idle(self.hide)
        return True

    def get_aviable_plugins(self):
        for pname in discover_plugins():
            failed = False
            try:
                package = get_plugin(pname)
            except:
                failed = True

            name = getattr(package, 'name', pname)
            desc = getattr(package, 'desc', 'Load failed' if failed else 'Some weird plugin')
            markup = "<b>%s</b>\n<small>%s</small>" % tuple(
                map(markup_escape_text, (name, desc)))

            yield (pname, markup, name)

    def fill_plugin_list(self, enabled):
        self.plugins.clear()

        for p in sorted(self.get_aviable_plugins(), key=lambda r: r[-1]):
            self.plugins.append((p[0] in enabled,) + p)

        self.plugins_tree.columns_autosize()
        self.plugins_tree.set_cursor("0", self.plugins_tree.get_columns()[0])

    def on_enabled_toggled(self, renderer, path):
        iter = self.plugins.get_iter(path)
        self.plugins.set_value(iter, 0, not renderer.get_active())
