import gtk
import gtksourceview2

from gsignals import connect_all

from .signals import EditorSignals

class Editor(object):
    """
    The main editor window.
    
    Editor can be both standalone window and embedded into tab. 
    """
    
    def __init__(self, filename):    
        self.signals = EditorSignals()
        
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect('delete-event', self.on_delete_event)
        self.window.connect('destroy', self.on_destroy)
        
        self.buffer = gtksourceview2.Buffer()
        self.view = gtksourceview2.View()
        
        self.view.props.buffer = self.buffer
        
        self.window.add(self.view)

        self.window.show_all()
        
        self.load_file(filename)

    def load_file(self, filename):
        if filename:
            lm = gtksourceview2.language_manager_get_default()
            lang = lm.guess_language(filename, None)
            
            self.buffer.set_language(lang)
            self.buffer.set_text(open(filename).read().decode('utf-8'))    
            self.window.set_title(filename)
        
    def on_destroy(self, *args):
        self.signals.editor_closed.emit(self)
    
    def on_delete_event(self, *args):
        return False
    
    def close(self):
        del self.window

        
class EditorManager(object):
    """
    Keeps window editor list
    """
    
    def __init__(self):
        self.editors = []
        
    def open(self, filename):
        editor = Editor(filename)
        self.editors.append(editor)
        connect_all(self, editor.signals)
        return editor
    
    @EditorSignals.editor_closed(idle=True)
    def editor_closed(self, sender, editor):
        self.editors.remove(editor)
        if not self.editors:
            gtk.main_quit()
