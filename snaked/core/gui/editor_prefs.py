import weakref

import gtksourceview2

from snaked.util import BuilderAware, join_to_file_dir, idle
from snaked.core import shortcuts
import snaked.core.prefs as prefs


class PreferencesDialog(BuilderAware):
    def __init__(self, prefs):
        BuilderAware.__init__(self, join_to_file_dir(__file__, 'editor_prefs.glade'))
        self.activator = shortcuts.ShortcutActivator(self.window)
        self.activator.bind('Escape', self.hide)

        self.prefs = prefs

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
        self.select_lang(editor.lang)
        self.refresh_lang_settings()
        self.window.present()

    def select_lang(self, lang_id):
        for i, (name,) in enumerate(self.langs):
            if name == lang_id:
                self.langs_view.set_cursor((i,))
                self.langs_view.scroll_to_cell((i,), None, True, 0.5, 0)
                return 
                
        self.langs_view.set_cursor((0,))
    
    def get_current_lang_id(self):
        (model, iter) = self.langs_view.get_selection().get_selected()
        return self.langs.get_value(iter, 0)
        
    def refresh_lang_settings(self, *args):
        lang_id = self.get_current_lang_id()
        
        pref = prefs.CompositePreferences(self.prefs.get(lang_id, {}),
            self.prefs.get('default', {}), prefs.default_prefs.get(lang_id, {}),
            prefs.default_prefs['default'])
        
        self.use_tabs.set_active(pref['use-tabs'])
        self.select_style(pref['style'])
            
    def select_style(self, style_id, try_classic=True):
        self.style_cb.old_value = style_id
        for i, (name,) in enumerate(self.styles):
            if name == style_id:
                self.style_cb.set_active(i)
                return 
        
        if try_classic:
            return self.select_style('classic', False)

        self.style_cb.set_active(0)

    def hide(self):
        prefs.save_json_settings('langs.conf', self.prefs)
        self.editor().message('Editor settings saved')
        self.window.destroy()

    def on_delete_event(self, *args):
        idle(self.hide)
        return True

    def on_style_cb_changed(self, *args):
        (style_id,) = self.styles[self.style_cb.get_active()]
        if style_id != self.style_cb.old_value:
            lang_id = self.get_current_lang_id()
            self.prefs.setdefault(lang_id, {})['style'] = style_id
            self.editor().settings_changed.emit()
        
    def on_reset_to_default_clicked(self, *args):
        try:
            del self.prefs[self.get_current_lang_id()]
        except KeyError:
            pass
        
        self.refresh_lang_settings()
        self.editor().settings_changed.emit()
