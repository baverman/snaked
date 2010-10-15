import weakref

from snaked.util import BuilderAware, join_to_file_dir, idle

import snaked.core.prefs as prefs

class PreferencesDialog(BuilderAware):
    def __init__(self):
        BuilderAware.__init__(self, join_to_file_dir(__file__, 'prefs.glade'))
        
        from snaked.core.shortcuts import ShortcutActivator
        self.activator = ShortcutActivator(self.window)
        self.activator.bind('Escape', self.hide)
        self.activator.bind('Return', self.activate)
        
    def hide(self):
        self.window.destroy()
        
    def show(self, editor):
        self.editor = weakref.ref(editor)
        self.fill_dialogs(None)
        editor.request_transient_for.emit(self.window)
        self.window.show()
        
    def fill_dialogs(self, search):
        self.dialogs.clear()

        for name, (keywords, show_func) in prefs.registered_dialogs.iteritems():
            if not search or any(w.startswith(search) for w in keywords):
                markup = '<b>%s</b>\n<small>%s</small>' % (
                    name, u' \u2022 '.join(keywords))
                self.dialogs.append((name, markup))
        
    def on_delete_event(self, *args):
        return False
        
    def on_search_entry_changed(self, *args):
        search = self.search_entry.get_text().strip().lower()
        idle(self.fill_dialogs, search)
        
    def activate(self):
        (model, iter) = self.dialogs_view.get_selection().get_selected()
        name = model.get_value(iter, 0)
        prefs.registered_dialogs[name][1](self.editor())
        idle(self.hide)