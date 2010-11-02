import weakref

import re

from snaked.util import BuilderAware, join_to_file_dir, idle
from snaked.core import shortcuts
from snaked.core.prefs import CompositePreferences, load_json_settings, save_json_settings

default_prefs = {
    'name': '',
    'langs': '',
    'command': '',
    'stdin': 'none',
    'stdout': 'show-feedback',
}

remove_tags = re.compile(r'<[^<]*?/?>')

class PreferencesDialog(BuilderAware):
    def __init__(self):
        BuilderAware.__init__(self, join_to_file_dir(__file__, 'prefs.glade'))
        self.activator = shortcuts.ShortcutActivator(self.window)
        self.activator.bind('Escape', self.hide)
        self.activator.bind('Delete', self.delete_tool)

        self.dirty_settings = {}
        self.tool_settings = load_json_settings('external-tools.conf', {})

        for name in sorted(self.tool_settings, reverse=True):
            self.tools.prepend((name,))

        for n in ('name', 'langs', 'command'):
            getattr(self, n).connect('changed', self.entry_changed, n)

        for n in ('stdin', 'stdout'):
            getattr(self, n+'_cb').connect('changed', self.cb_changed, n)

    def get_name(self, name):
        return remove_tags.sub('', name).strip().replace('_', '')

    def show(self, editor):
        self.editor = weakref.ref(editor)
        editor.request_transient_for.emit(self.window)
        self.select_tool('New tool')
        self.tools_view.columns_autosize()
        self.window.present()

    def save_settings(self):
        settings = {}
        for v in self.tool_settings.values():
            settings[self.get_name(v['name'])] = v
        save_json_settings('external-tools.conf', settings)

    def hide(self):
        self.save_settings()
        self.editor().message('External tool settings saved')
        idle(self.window.destroy)

    @property
    def current_tool(self):
        (model, iter) = self.tools_view.get_selection().get_selected()
        return self.tools.get_value(iter, 0)

    @property
    def settings(self):
        name = self.current_tool
        if self.isnew(name):
            return self.dirty_settings
        else:
            return self.tool_settings.setdefault(name, {})

    def isnew(self, tool):
        return tool == 'New tool'

    def entry_changed(self, entry, name):
        self.settings[name] = entry.get_text()

    def cb_changed(self, cb, name):
        self.settings[name] = cb.get_model().get_value(cb.get_active_iter(), 0)

    def select_tool(self, name):
        for i, (n,) in enumerate(self.tools):
            if n == name:
                self.tools_view.set_cursor((i,))
                return

        self.tools_view.set_cursor((len(self.tools)-1,))

    def set_cb(self, cb, value):
        for i, (id, _) in enumerate(cb.get_model()):
            if id == value:
                cb.set_active(i)
                return

        cb.set_active(0)

    def on_tools_view_cursor_changed(self, *args):
        name = self.current_tool
        prefs = CompositePreferences(self.settings, default_prefs)

        if self.isnew(name):
            self.add_btn.get_parent().show()
        else:
            self.add_btn.get_parent().hide()

        for n in ('name', 'langs', 'command'):
            getattr(self, n).set_text(prefs[n])

        for n in ('stdin', 'stdout'):
            self.set_cb(getattr(self, n+'_cb'), prefs[n])

    def on_add_btn_clicked(self, *args):
        name = self.get_name(self.dirty_settings.get('name', ''))
        if not name or self.isnew(name):
            self.editor().message('Enter tool name')
            return
        elif name in self.tool_settings:
            self.editor().message('Tool already exists')
            return

        prefs = CompositePreferences(self.dirty_settings,
            self.tool_settings.get('name', {}), default_prefs)

        new_prefs = self.tool_settings.setdefault(name, {})
        for k in default_prefs:
            new_prefs[k] = prefs[k]

        self.tools.insert(len(self.tools)-1, (name,))
        self.select_tool(name)
        idle(self.tools_view.grab_focus)
        self.dirty_settings.clear()

    def on_window_delete_event(self, *args):
        self.hide()

    def delete_tool(self, *args):
        name = self.current_tool
        if self.isnew(name):
            self.editor().message('Lolwhat?')
            return

        (model, iter) = self.tools_view.get_selection().get_selected()
        path = model.get_path(iter)
        model.remove(iter)
        del self.tool_settings[name]
        self.tools_view.set_cursor(path)