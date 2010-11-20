import gtk
from gobject import timeout_add, source_remove

class EscapeObject(object): pass

class FeedbackPopup(object):
    def __init__(self):

        self.window = gtk.Window(gtk.WINDOW_POPUP)
        self.window.set_property('allow-shrink', True)

        self.bar = gtk.EventBox()
        self.bar.set_border_width(5)

        box = gtk.EventBox()

        self.label = gtk.Label()
        self.label.set_alignment(0, 0)
        self.label.set_padding(10, 0)
        box.add(self.label)

        self.bar.add(box)
        self.bar.show_all()

        self.window.add(self.bar)

        self.timeout_id = None

        self.escape = None

    def remove_timeout(self):
        if self.timeout_id:
            source_remove(self.timeout_id)

        self.timeout_id = None

    def show(self, editor, text, timeout=1500):
        self.remove_timeout()
        if self.escape:
            self.hide()

        self.label.set_text(text)
        self.window.resize(*self.window.size_request())

        win = editor.view.get_window(gtk.TEXT_WINDOW_TEXT)
        x, y, w, h, _ = win.get_geometry()
        x, y = win.get_origin()
        mw, mh = self.window.get_size()

        self.window.move(x + w - mw, y + h - mh)
        self.window.show()

        if not self.escape:
            self.escape = EscapeObject()

        self.timeout_id = timeout_add(timeout, self.hide)

    def hide(self, *args):
        self.remove_timeout()
        self.window.hide()
        self.escape = None
        return False
