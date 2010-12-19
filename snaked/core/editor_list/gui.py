import weakref

import pango, gtk

from snaked.util import idle, join_to_file_dir, BuilderAware, refresh_gui
from snaked.core.shortcuts import ShortcutActivator

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

        self.path2editor = weakref.WeakValueDictionary()
        self.editors_view.set_search_equal_func(search_func)
        self.editors_view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

    def show(self, editor, editors):
        self.first_show = self.editor is None
        self.editor = weakref.ref(editor)
        self.editor_list = editors

        self.block_cursor = True
        self.fill()
        editor.request_transient_for.emit(self.window)
        self.window.present()
        self.block_cursor = False

    def fill(self):
        self.editors.clear()
        self.path2editor.clear()

        active_editor = self.editor()
        titles = [(e.get_title.emit(), e) for e in self.editor_list]
        for t, e in sorted(titles, key=lambda r: r[0]):
            weight = pango.WEIGHT_BOLD if e is active_editor else pango.WEIGHT_NORMAL
            iter = self.editors.append(None, (t, weight))
            path = self.editors.get_path(iter)
            self.path2editor[path] = e

        self.editors_view.columns_autosize()

    def hide(self):
        self.window.hide()

    def on_delete_event(self, *args):
        self.escape()
        return True

    def close_editor(self, *args):
        model, pathes = self.editors_view.get_selection().get_selected_rows()
        for p in pathes:
            self.path2editor[p].request_close.emit()

        refresh_gui()
        idle(self.fill)

    def on_editors_view_row_activated(self, view, path, *args):
        idle(self.editor().open_file, self.path2editor[path].uri)
        idle(self.hide)

    def on_editors_view_cursor_changed(self, *args):
        if self.editor and not self.block_cursor:
            path, _ = self.editors_view.get_cursor()
            idle(self.editor().open_file, self.path2editor[path].uri)
