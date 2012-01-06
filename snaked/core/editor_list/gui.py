import weakref

import pango, gtk

from uxie.utils import idle, join_to_file_dir, refresh_gui
from uxie.misc import BuilderAware
from uxie.actions import Activator

mnemonics = '1234567890abcdefghigklmnopqrstuvwxyz'

def search_func(model, column, key, iter):
    if key in model.get_value(iter, 0):
        return False

    return True

class EditorListDialog(BuilderAware):
    """glade-file: gui.glade"""

    def __init__(self):
        super(EditorListDialog, self).__init__(join_to_file_dir(__file__, 'gui.glade'))

        from snaked.core.manager import keymap
        self.activator = keymap.get_activator(self.window)
        self.activator.bind('any', 'escape', None, self.hide)
        self.activator.bind('any', 'delete', None, self.close_editor)

        self.block_cursor = False

        self.path2uri = {}
        self.paths = []
        self.editors_view.set_search_equal_func(search_func)
        self.editors_view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        self.model = gtk.ListStore(str, int, str, object, str)
        self.editors_view.set_model(self.model)

        self.mnemonic_renderer.set_property('yalign', 0.5)
        self.mnemonic_renderer.set_property('weight', pango.WEIGHT_BOLD)
        self.mnemonic_renderer.set_property('width', 5)
        self.mnemonic_hole.set_property('width', 20)

        for m in mnemonics:
            self.activator.bind('any', 'activate-mnemonic-'+m,
                None, self.mnemonic_activate, m).to('<alt>'+m)

    def show(self, window, recent_editors):
        self.pwindow = weakref.ref(window)
        self.recent_editors = recent_editors

        self.block_cursor = True
        self.fill()
        self.window.set_transient_for(window)
        self.window.present()
        self.block_cursor = False

    @property
    def editor_list(self):
        return list(self.pwindow().manager.get_editors())

    @property
    def current_editor(self):
        return self.pwindow().get_editor_context()

    def fill(self):
        self.model.clear()

        active_editor = self.current_editor
        titles = [(e.get_title.emit(), e) for e in self.editor_list]
        editor_uris = set()

        def append(uri, title, editor, weight, mnemonic_idx):
            if mnemonic_idx < len(mnemonics):
                m = '<b><small>%s</small></b>' % mnemonics[mnemonic_idx]
                ml = mnemonics[mnemonic_idx]
            else:
                m = ''
                ml = ''

            self.model.append((title, weight, m, (uri, weakref.ref(editor) if editor else None), ml))

        for i, (t, e) in enumerate(sorted(titles, key=lambda r: r[0])):
            editor_uris.add(e.uri)
            weight = pango.WEIGHT_BOLD if e is active_editor else pango.WEIGHT_NORMAL
            append(e.uri, t, e, weight, i)

        recent_titles = [(u, t) for u, t in self.recent_editors.items() if u not in editor_uris]
        if recent_titles:
            self.model.append(('----=== Recent ===----', pango.WEIGHT_NORMAL, '', (None, None), ''))
            for u, t in sorted(recent_titles, key=lambda r: r[1]):
                i += 1
                append(u, t, None, pango.WEIGHT_NORMAL, i)

    def hide(self):
        self.window.hide()

    def on_delete_event(self, *args):
        self.escape()
        return True

    def close_editor(self, *args):
        model, pathes = self.editors_view.get_selection().get_selected_rows()
        for p in pathes:
            u, e = model[p][3]
            if e and e():
                e().close()

        refresh_gui()
        if self.editor_list:
            idle(self.fill)
        else:
            self.hide()

    def activate_editor(self, path):
        uri, editor = self.model[path][3]
        if editor and editor():
            ce = self.current_editor
            if ce:
                ce.add_spot()
            idle(editor().focus)
            idle(self.hide)
        elif uri:
            ce = self.current_editor
            if ce:
                ce.add_spot()
            idle(self.pwindow().open_or_activate, uri)
            idle(self.hide)

    def on_editors_view_row_activated(self, view, path, *args):
        self.activate_editor(path)

    def on_editors_view_cursor_changed(self, *args):
        pwindow = self.pwindow()
        if pwindow and pwindow.manager.conf['EDITOR_LIST_SWITCH_ON_SELECT'] and not self.block_cursor:
            path, _ = self.editors_view.get_cursor()
            uri, editor = self.model[path][3]
            if editor and editor():
                idle(editor().focus)

    def mnemonic_activate(self, m):
        for r in self.model:
            if r[4] == m:
                self.activate_editor(r.path)