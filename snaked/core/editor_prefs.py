import weakref

import gtksourceview2

from snaked.util import BuilderAware, join_to_file_dir, idle
from snaked.core import shortcuts

class PreferencesDialog(BuilderAware):
    def __init__(self, prefs, default_prefs):
        BuilderAware.__init__(self, join_to_file_dir(__file__, 'editor_prefs.glade'))
        self.activator = shortcuts.ShortcutActivator(self.window)
        self.activator.bind('Escape', self.hide)

        self.prefs = prefs
        self.default_prefs = default_prefs

        self.langs.append(('default', ))
        lm = gtksourceview2.language_manager_get_default()
        for lang_id in sorted(lm.get_language_ids()):
            self.langs.append((lang_id, ))

        sm = gtksourceview2.style_scheme_manager_get_default()
        for style_id in sm.get_scheme_ids():
            self.styles.append((style_id, ))
        
    def show(self, editor):
        self.editor = weakref.ref(editor)        
        editor.request_transient_for.emit(self.window)
        real_lang = self.select_lang(editor.lang)
        self.window.present()

    def select_lang(self, lang_id):
        for i, (name,) in enumerate(self.langs):
            if name == lang_id:
                self.langs_view.set_cursor((i,))
                self.langs_view.scroll_to_cell((i,), None, True, 0.5, 0)
                return name

        self.langs_view.set_cursor((0,))
        return 'default'
        
    def hide(self):
        self.editor().message('Editor settings saved')
        self.window.destroy()

    def on_delete_event(self, *args):
        idle(self.hide)
        return True
