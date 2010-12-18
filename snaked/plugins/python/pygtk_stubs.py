import gtk

class TextView(gtk.TextView):
    def get_buffer(self):
        return gtk.TextBuffer()

class TextBuffer(gtk.TextBuffer):
    def get_iter_at_mark(self, mark):
        return gtk.TextIter()