import weakref

from snaked.util import BuilderAware, join_to_file_dir, idle, set_activate_the_one_item

import snaked.core.prefs as prefs

class PreferencesDialog(BuilderAware):
    def __init__(self):
        BuilderAware.__init__(self, join_to_file_dir(__file__, 'prefs.glade'))

        from snaked.core.shortcuts import ShortcutActivator
        self.activator = ShortcutActivator(self.window)
        self.activator.bind('Escape', self.hide)
        self.activator.bind('<alt>s', self.focus_search)

        set_activate_the_one_item(self.search_entry, self.dialogs_view)

    def hide(self):
        self.window.destroy()

    def show(self, editor):
        self.editor = weakref.ref(editor)
        self.fill_dialogs(None)
        editor.request_transient_for.emit(self.window)
        self.window.show()

    def fill_dialogs(self, search):
        self.dialogs.clear()

        for name in sorted(prefs.registered_dialogs):
            keywords, show_func = prefs.registered_dialogs[name]
            if not search or any(w.startswith(search) for w in keywords):
                markup = '<b>%s</b>\n<small>%s</small>' % (
                    name, u' \u2022 '.join(keywords))
                self.dialogs.append((name, markup))

    def on_delete_event(self, *args):
        return False

    def on_search_entry_changed(self, *args):
        search = self.search_entry.get_text().strip().lower()
        idle(self.fill_dialogs, search)

    def activate(self, *args):
        (model, iter) = self.dialogs_view.get_selection().get_selected()
        if iter:
            name = model.get_value(iter, 0)
            prefs.registered_dialogs[name][1](self.editor())
            idle(self.hide)
        else:
            self.editor().message('You need select item')

    def focus_search(self):
        self.search_entry.grab_focus()