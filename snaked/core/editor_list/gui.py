import weakref

import pango, gtk

from snaked.util import idle, join_to_file_dir, BuilderAware, refresh_gui
from snaked.core.shortcuts import ShortcutActivator

mnemonics = '1234567890abcdefghigklmnopqrstuvwxyz'

def search_func(model, column, key, iter):
    if key in model.get_value(iter, 0):
        return False

    return True

class EditorListDialog(BuilderAware):
    """glade-file: gui.glade"""

    def __init__(self):
        super(EditorListDialog, self).__init__(join_to_file_dir(__file__, 'gui.glade'))
        self.shortcuts = ShortcutActivator(self.window)
        self.shortcuts.bind('Escape', self.hide)
        self.shortcuts.bind('Delete', self.close_editor)

        self.editor = None
        self.block_cursor = False

        self.path2uri = {}
        self.paths = []
        self.editors_view.set_search_equal_func(search_func)
        self.editors_view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        self.mnemonic_renderer.set_property('yalign', 0.5)
        self.mnemonic_renderer.set_property('weight', pango.WEIGHT_BOLD)
        self.mnemonic_renderer.set_property('width', 5)
        self.mnemonic_hole.set_property('width', 20)

        for i, m in enumerate(mnemonics):
            self.shortcuts.bind('<alt>'+m, self.mnemonic_activate, i)

    def show(self, editor, editors, recent_editors):
        self.first_show = self.editor is None
        self.editor = weakref.ref(editor)
        self.editor_list = editors
        self.recent_editors = recent_editors

        self.block_cursor = True
        self.fill()
        editor.request_transient_for.emit(self.window)
        self.window.present()
        self.block_cursor = False

    def fill(self):
        self.editors.clear()
        self.path2uri.clear()
        self.paths[:] = []

        active_editor = self.editor()
        titles = [(e.get_title.emit(), e) for e in self.editor_list]
        editor_uris = {}

        def append(uri, title, weight, mnemonic_idx):
            if mnemonic_idx < len(mnemonics):
                m = '<b><small>%s</small></b>' % mnemonics[mnemonic_idx]
            else:
                m = ''

            iter = self.editors.append(None, (title, weight, m))
            path = self.editors.get_path(iter)
            self.path2uri[path] = uri
            self.paths.append(path)

        for i, (t, e) in enumerate(sorted(titles, key=lambda r: r[0])):
            editor_uris[e.uri] = True
            weight = pango.WEIGHT_BOLD if e is active_editor else pango.WEIGHT_NORMAL
            append(e.uri, t, weight, i)

        recent_titles = [(u, t) for u, t in self.recent_editors.items() if u not in editor_uris]
        if recent_titles:
            self.editors.append(None, ('----=== Recent ===----', pango.WEIGHT_NORMAL, ''))
            for u, t in sorted(recent_titles, key=lambda r: r[1]):
                i += 1
                append(u, t, pango.WEIGHT_NORMAL, i)

    def hide(self):
        self.window.hide()

    def on_delete_event(self, *args):
        self.escape()
        return True

    def close_editor_by_uri(self, uri):
        for e in self.editor_list:
            if uri == e.uri:
                e.request_close.emit()
                break

    def close_editor(self, *args):
        model, pathes = self.editors_view.get_selection().get_selected_rows()
        for p in pathes:
            if p in self.path2uri:
                self.close_editor_by_uri(self.path2uri[p])

        refresh_gui()
        if self.editor_list:
            idle(self.fill)
        else:
            self.hide()

    def activate_editor(self, path):
        if path in self.path2uri:
            idle(self.editor().open_file, self.path2uri[path])
            idle(self.hide)

    def on_editors_view_row_activated(self, view, path, *args):
        self.activate_editor(path)

    def on_editors_view_cursor_changed(self, *args):
        editor = self.editor()
        if editor and editor.snaked_conf['EDITOR_LIST_SWITCH_ON_SELECT'] and not self.block_cursor:
            path, _ = self.editors_view.get_cursor()
            if path in self.path2uri:
                idle(editor.open_file, self.path2uri[path])

    def mnemonic_activate(self, idx):
        if idx < len(self.paths):
            self.activate_editor(self.paths[idx])