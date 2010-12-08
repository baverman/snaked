import weakref

from gtk import accelerator_name, accel_map_change_entry
from pango import WEIGHT_BOLD, WEIGHT_NORMAL

from snaked.util import BuilderAware, join_to_file_dir, idle
from snaked.core import shortcuts

class ShortcutsDialog(BuilderAware):
    def __init__(self):
        BuilderAware.__init__(self, join_to_file_dir(__file__, 'shortcuts.glade'))
        self.activator = shortcuts.ShortcutActivator(self.window)
        self.activator.bind('Escape', self.hide)

    def show(self, editor):
        self.editor = weakref.ref(editor)
        self.fill_actions()
        editor.request_transient_for.emit(self.window)
        self.window.present()

    def get_weight(self, path, key, mod):
        return WEIGHT_BOLD if shortcuts.default_shortcuts[path] != (key, mod) else WEIGHT_NORMAL

    def fill_actions(self):
        self.actions_view.set_model(None)

        categories = {}
        sortkey = lambda v: v[0]

        for path, key, mod in sorted(shortcuts.get_registered_shortcuts(), key=sortkey):
            _, category, name = path.split('/')

            accel = accelerator_name(key, mod)
            try:
                desc = shortcuts.registered_shortcuts[name][1]
            except KeyError:
                continue

            if category not in categories:
                categories[category] = self.actions.append(
                    None, (category, None, None, False, WEIGHT_NORMAL))

            self.actions.append(categories[category], (name, accel, desc, True,
                self.get_weight(path, key, mod)))

        self.actions_view.set_model(self.actions)
        self.actions_view.expand_all()

    def hide(self):
        shortcuts.save_shortcuts()
        self.editor().message('Key configuration saved')
        self.window.destroy()

    def on_delete_event(self, *args):
        idle(self.hide)
        return True

    def on_accel_edited(self, renderer, path, accel_key, accel_mods, hardware_keycode):
        iter = self.actions.get_iter(path)
        accel = accelerator_name(accel_key, accel_mods)
        name = self.actions.get_value(iter, 0)
        path = shortcuts.get_path_by_name(name)

        accel_map_change_entry(path, accel_key, accel_mods, True)
        shortcuts.names_by_key.clear()

        self.actions.set_value(iter, 1, accel)
        self.actions.set_value(iter, 4, self.get_weight(path, accel_key, accel_mods))

    def on_accel_cleared(self, renderer, path, *args):
        iter = self.actions.get_iter(path)
        name = self.actions.get_value(iter, 0)
        path = shortcuts.get_path_by_name(name)

        accel_map_change_entry(path, 0, 0, True)
        shortcuts.names_by_key.clear()

        self.actions.set_value(iter, 1, None)
        self.actions.set_value(iter, 4, WEIGHT_BOLD)
