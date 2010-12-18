import gtk

class Lolwhat(object):
    def star(self):
        pass

    def superstar(self):
        pass

class Trololo(object):
    def eduard(self):
        pass

    def hill(self):
        pass

class ModifiedTrololo(Trololo):
    def anatolievich(self):
        pass

class ModifiedTextView(gtk.TextView):
    def get_buffer(self):
        return gtk.TextBuffer()