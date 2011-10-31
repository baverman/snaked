import weakref

import gtksourceview2

from uxie.utils import join_to_file_dir, idle
from uxie.misc import BuilderAware
from uxie.actions import Activator

import snaked.core.prefs as prefs

on_dialog_created_hooks = []
on_pref_refresh_hooks = []


class PreferencesDialog(BuilderAware):
    def __init__(self, prefs):
        BuilderAware.__init__(self, join_to_file_dir(__file__, 'editor_prefs.glade'))

        from snaked.core.manager import keymap
        self.activator = keymap.get_activator(self.window)
        self.activator.bind('any', 'escape', None, self.hide)

        self.prefs = prefs
        self.original_prefs = prefs.copy()

        self.langs.append(('default', ))
        lm = gtksourceview2.language_manager_get_default()
        for lang_id in sorted(lm.get_language_ids()):
            self.langs.append((lang_id, ))

        sm = gtksourceview2.style_scheme_manager_get_default()
        for style_id in sorted(sm.get_scheme_ids()):
            self.styles.append((style_id, ))

        self.checks = ['use-tabs', 'show-right-margin', 'show-line-numbers', 'wrap-text',
            'highlight-current-line', 'show-whitespace', 'remove-trailing-space']

        for name in self.checks:
            getattr(self, name.replace('-', '_')).connect(
                'toggled', self.on_checkbox_toggled, name)

        self.margin_width.connect('value-changed', self.on_spin_changed, 'right-margin')
        self.tab_width.connect('value-changed', self.on_spin_changed, 'tab-width')
        self.line_spacing.connect('value-changed', self.on_spin_changed, 'line-spacing')

        self.font.connect('font-set', self.on_font_set, 'font')

        for h in on_dialog_created_hooks:
            h(self)

    def show(self, window):
        self.pwindow = weakref.ref(window)
        self.window.set_transient_for(window)

        editor = window.get_editor_context()
        if editor:
            self.select_lang(editor.lang)
        else:
            self.select_lang(default)

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

    def get_lang_prefs(self, lang_id):
        if lang_id == 'default':
            return prefs.CompositePreferences(self.prefs.get('default', {}),
                prefs.default_prefs.get(lang_id, {}), prefs.default_prefs['default'])
        else:
            return prefs.CompositePreferences(self.prefs.get(lang_id, {}),
                self.prefs.get('default', {}), prefs.default_prefs.get(lang_id, {}),
                prefs.default_prefs['default'])

    def get_default_lang_prefs(self, lang_id):
        if lang_id == 'default':
            return prefs.CompositePreferences(prefs.default_prefs.get(lang_id, {}),
                prefs.default_prefs['default'])
        else:
            return prefs.CompositePreferences(self.prefs.get('default', {}),
                prefs.default_prefs.get(lang_id, {}), prefs.default_prefs['default'])

    def set_checkbox(self, pref, name):
        getattr(self, name.replace('-', '_')).set_active(pref[name])

    def refresh_lang_settings(self, *args):
        pref = self.get_lang_prefs(self.get_current_lang_id())

        for name in self.checks:
            self.set_checkbox(pref, name)

        self.select_style(pref['style'])

        self.margin_width.set_value(pref['right-margin'])
        self.tab_width.set_value(pref['tab-width'])
        self.line_spacing.set_value(pref['line-spacing'])

        self.font.set_font_name(pref['font'])

        for h in on_pref_refresh_hooks:
            h(self, pref)

    def select_style(self, style_id, try_classic=True):
        for i, (name,) in enumerate(self.styles):
            if name == style_id:
                self.style_cb.set_active(i)
                return

        if try_classic:
            return self.select_style('classic', False)

        self.style_cb.set_active(0)

    def hide(self):
        self.save_settings()
        self.pwindow().emessage('Editor settings saved')
        self.window.destroy()

    def save_settings(self):
        prefs.save_json_settings('langs.conf', self.prefs)

    def on_delete_event(self, *args):
        idle(self.hide)
        return True

    def update_editor_settings(self):
        manager = self.pwindow().manager
        editor = self.pwindow().get_editor_context()
        buf = editor.buffer if editor else None

        if editor:
            manager.set_buffer_prefs(buf, buf.uri, buf.lang)
            editor.update_view_preferences()

        for b in manager.buffers:
            if b is not buf:
                idle(manager.set_buffer_prefs, b, b.uri, b.lang)

        for e in manager.get_editors():
            if e is not editor:
                idle(e.update_view_preferences)

    def update_pref_value(self, lang_id, name, value):
        current_value = self.get_lang_prefs(lang_id)[name]
        if value != current_value:
            default_value = self.get_default_lang_prefs(lang_id)[name]
            if value == default_value:
                try:
                    del self.prefs[lang_id][name]
                except KeyError:
                    pass
            else:
                self.prefs.setdefault(lang_id, {})[name] = value

            self.update_editor_settings()

    def on_style_cb_changed(self, *args):
        (style_id,) = self.styles[self.style_cb.get_active()]
        lang_id = self.get_current_lang_id()
        self.update_pref_value(lang_id, 'style', style_id)

    def on_checkbox_toggled(self, widget, name):
        self.update_pref_value(self.get_current_lang_id(), name, widget.get_active())

    def on_spin_changed(self, widget, name):
        self.update_pref_value(self.get_current_lang_id(), name, widget.get_value_as_int())

    def on_font_set(self, widget, name):
        self.update_pref_value(self.get_current_lang_id(), name, widget.get_font_name())

    def on_reset_to_default_clicked(self, *args):
        try:
            del self.prefs[self.get_current_lang_id()]
        except KeyError:
            pass

        self.refresh_lang_settings()
        self.update_editor_settings()
