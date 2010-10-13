import gtk

from snaked.core.shortcuts import ContextShortcutActivator
import snaked.core.editor

class TabbedEditorManager(snaked.core.editor.EditorManager):
    def __init__(self):
        super(TabbedEditorManager, self).__init__()

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect('delete-event', self.on_delete_event)

        self.window.set_property('default-width', 800)
        self.window.set_property('default-height', 500)
    
        self.activator = ContextShortcutActivator(self.window, self.get_context)
        
        self.note = gtk.Notebook()
        self.note.set_property('tab-hborder', 10)
        self.note.set_property('homogeneous', False)
        self.note.connect_after('switch-page', self.on_switch_page)
        self.window.add(self.note)
        
        self.window.show_all()
    
    def get_context(self):
        widget = self.note.get_nth_page(self.note.get_current_page())
        for e in self.editors:
            if e.widget is widget:
                return (e,)

        raise Exception('Editor not found')

    def manage_editor(self, editor):
        label = gtk.Label('Unknown')
        self.note.append_page(editor.widget, label)
        self.focus_editor(editor)
        editor.view.grab_focus()
       
    def focus_editor(self, editor):
        idx = self.note.page_num(editor.widget)
        self.note.set_current_page(idx)

    def update_top_level_title(self):
        idx = self.note.get_current_page()
        if idx < 0:
            return
        
        title = self.note.get_tab_label_text(self.note.get_nth_page(idx))
        if title is not None:
            self.window.set_title(title)        
                
    def set_editor_title(self, editor, title):
        self.note.set_tab_label_text(editor.widget, title)
        if self.note.get_current_page() == self.note.page_num(editor.widget):
            self.update_top_level_title()

    def on_delete_event(self, *args):
        self.quit()

    def close_editor(self, editor):
        idx = self.note.page_num(editor.widget)
        self.note.remove_page(idx)
        editor.editor_closed.emit()

    def set_editor_shortcuts(self, editor):
        self.plugin_manager.bind_shortcuts(self.activator, editor)

        if hasattr(self, 'editor_shortcuts_binded'):
            return
        
        self.editor_shortcuts_binded = True

        self.activator.bind_to_name('quit', self.quit)
        self.activator.bind_to_name('close-window', self.close_editor)
        self.activator.bind_to_name('save', self.save)
        self.activator.bind_to_name('next-editor', self.switch_to, 1)
        self.activator.bind_to_name('prev-editor', self.switch_to, -1)
        self.activator.bind_to_name('new-file', self.new_file_action)

        self.activator.bind_to_name('show-preferences', self.show_preferences)

        self.activator.bind('Escape', self.process_escape)

    def quit(self, *args):
        self.window.hide()
        super(TabbedEditorManager, self).quit()

    def save(self, editor):
        editor.save()

    def set_transient_for(self, editor, window):
        window.set_transient_for(self.window)

    def on_switch_page(self, *args):
        self.update_top_level_title()
        
    def switch_to(self, editor, dir):
        idx = ( self.note.get_current_page() + dir ) % self.note.get_n_pages()
        self.note.set_current_page(idx)
