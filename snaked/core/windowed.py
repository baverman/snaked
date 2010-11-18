import weakref

import gtk

import snaked.core.shortcuts
import snaked.core.editor

class WindowedEditorManager(snaked.core.editor.EditorManager):
    def __init__(self):
        super(WindowedEditorManager, self).__init__()
        self.windows = weakref.WeakKeyDictionary()
        self.activators = weakref.WeakKeyDictionary()

    def on_window_destroy(self, window, editor):
        editor().editor_closed.emit()

    def manage_editor(self, editor):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_default_size(800, 550)
        window.add(editor.widget)
        
        editor.view.grab_focus()
        
        weak_editor = weakref.ref(editor)
        def ctx():
            return (weak_editor(), )
        
        activator = snaked.core.shortcuts.ContextShortcutActivator(window, ctx)
        self.windows[editor] = window
        self.activators[editor] = activator

        window.connect('destroy', self.on_window_destroy, weak_editor)
        window.show_all()
       
    def focus_editor(self, editor):
        self.windows[editor].present()
        
    def set_editor_title(self, editor, title):
        self.windows[editor].set_title(title)
        
    def close_editor(self, editor):
        self.windows[editor].destroy()

    def set_editor_shortcuts(self, editor):
        activator = self.activators[editor]
        self.plugin_manager.bind_shortcuts(activator, editor)

        activator.bind_to_name('quit', self.quit)
        activator.bind_to_name('close-window', self.close_editor)
        activator.bind_to_name('save', self.save)
        activator.bind_to_name('new-file', self.new_file_action)

        activator.bind_to_name('show-preferences', self.show_preferences)

        activator.bind('Escape', self.process_escape)

    def save(self, editor):
        editor.save()

    def set_transient_for(self, editor, window):
        try:
            window.set_transient_for(self.windows[editor])
        except KeyError:
            pass
