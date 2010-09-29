from snaked.core.signals import EditorSignals
from snaked.util import single_ref

class Plugin(object):
    def __init__(self, editor):
        self.editor = editor
        self.editor.signals.connect_signals(self)
        
    @EditorSignals.file_loaded
    def on_file_loaded(self, *args):
        if self.editor.uri in self.prefs:
            from snaked.util import refresh_gui
            refresh_gui()
            iterator = self.editor.buffer.get_iter_at_line(int(self.prefs[self.editor.uri]))
            self.editor.buffer.place_cursor(iterator)
            self.editor.view.scroll_to_iter(iterator, 0.001, use_align=True, xalign=1.0)
    
    @EditorSignals.before_close
    def on_editor_before_close(self, *args):
        self.prefs[self.editor.uri] = str(self.editor.cursor.get_line())
                
    @single_ref
    def prefs(self):
        from snaked.core.prefs import KVSettings
        return KVSettings('positions.db')
