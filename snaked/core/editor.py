import os.path
import time

import weakref

import gtk
import gtksourceview2

from ..util import save_file, idle, get_project_root, single_ref
from ..signals import SignalManager, Signal, connect_all, connect_external

class Editor(SignalManager):
    add_spot_request = Signal()

    before_close = Signal()
    before_file_save = Signal(return_type=bool) # Handlers can return True to prevent file saving

    change_title = Signal(str)
    editor_closed = Signal()

    file_loaded = Signal()
    file_saved = Signal()

    get_file_position = Signal(return_type=int)
    get_project_larva = Signal(return_type=str)
    get_title = Signal(return_type=str)
    get_window_title = Signal(return_type=str)

    plugins_changed = Signal()
    push_escape_callback = Signal(object, object)

    request_close = Signal()
    request_to_open_file = Signal(str, object, object, return_type=object)
    request_transient_for = Signal(object)

    settings_changed = Signal()
    stack_add_request = Signal(object, object)
    stack_popup_request = Signal(object)

    def __init__(self, snaked_conf):
        self.uri = None
        self.session = None
        self.saveable = True
        self.lang = None
        self.contexts = []
        self.prefs = {}

        self.last_cursor_move = None

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)

        self.buffer = gtksourceview2.Buffer()

        self.view = gtksourceview2.View()
        self.view.set_buffer(self.buffer)
        sw.add(self.view)
        self.view.editor_ref = weakref.ref(self)

        self.widget = gtk.VBox(False, 0)
        self.widget.pack_start(sw)

        self.widget.show_all()

        connect_all(self, buffer=self.buffer, view=self.view)

        if snaked_conf['DISABLE_LEFT_CLICK']:
            self.view.connect('button-press-event', self.on_button_press_event)

        self.snaked_conf = snaked_conf

    def update_title(self):
        if self.uri:
            title = self.get_title.emit()

            if not title:
                title = os.path.basename(self.uri)
        else:
            title = 'Unknown'

        self.change_title.emit(title)

    def load_file(self, filename, line=None):
        self.uri = os.path.abspath(filename)
        self.encoding = 'utf-8'

        if os.path.exists(self.uri):
            self.view.window.freeze_updates()
            self.on_modified_changed_handler.block()
            self.buffer.begin_not_undoable_action()

            text = open(filename).read()

            try:
                utext = text.decode('utf-8')
            except UnicodeDecodeError, e:
                try:
                    import chardet
                    result = chardet.detect(text)
                    if result['encoding']:
                        utext = text.decode(result['encoding'])
                        self.encoding = result['encoding']
                        idle(self.message, 'Automatically selected ' + self.encoding + 'encoding', 5000)
                    else:
                        self.saveable = False
                        utext = 'Is this a text file?'
                except ImportError:
                    self.saveable = False
                    utext = str(e)
                except UnicodeDecodeError, ee:
                    self.saveable = False
                    utext = str(ee)

            self.buffer.set_text(utext)
            self.buffer.set_modified(False)

            self.buffer.end_not_undoable_action()

            if 'MODIFIED_FILES' in self.snaked_conf and self.uri in self.snaked_conf['MODIFIED_FILES']:
                tmpfilename = self.snaked_conf['MODIFIED_FILES'][self.uri]
                if os.path.exists(tmpfilename):
                    self.buffer.begin_user_action()
                    utext = open(tmpfilename).read().decode(self.encoding)
                    self.buffer.set_text(utext)
                    self.buffer.end_user_action()

            self.on_modified_changed_handler.unblock()
            self.view.window.thaw_updates()

            pos = line if line is not None else self.get_file_position.emit()
            if pos is not None and pos >= 0:
                self.buffer.place_cursor(self.buffer.get_iter_at_line(pos))
                self.view.scroll_to_mark(self.buffer.get_insert(), 0.001, use_align=True, xalign=1.0)
            else:
                self.buffer.place_cursor(self.buffer.get_start_iter())

        self.file_loaded.emit()

        self.update_title()

    @connect_external('buffer', 'modified-changed', idle=True)
    def on_modified_changed(self, *args):
        self.update_title()

    def save(self):
        if not self.saveable:
            self.message("This file was opened with error and can't be saved")
            return

        if self.uri:
            if self.before_file_save.emit():
                return

            if self.prefs['remove-trailing-space']:
                from snaked.core.processors import remove_trailing_spaces
                remove_trailing_spaces(self.buffer)

            try:
                save_file(self.uri, self.utext, self.encoding)
                if not self.buffer.get_modified():
                    self.message("%s saved" % self.uri)
                self.buffer.set_modified(False)
                self.file_saved.emit()
            except Exception, e:
                self.message(str(e), 5000)

    @property
    def project_root(self):
        """This is real file's project root

        There config can be saved and so on.

        """
        return self.get_project_root()

    def get_project_root(self, larva=False, force_select=False):
        if not self.uri:
            return None

        root = get_project_root(self.uri)

        if not root and force_select:
            pass

        if not root and larva:
            root = self.get_project_larva.emit()
            if not root:
                root = os.path.dirname(self.uri)

        return root

    def open_file(self, filename, line=None, lang_id=None):
        """:rtype: Editor"""
        return self.request_to_open_file.emit(filename, line, lang_id)

    @property
    def cursor(self):
        """Return buffer's cursor iter

        :rtype: gtk.TextIter
        """
        return self.buffer.get_iter_at_mark(self.buffer.get_insert())

    @property
    def text(self):
        """Return buffer's content as utf-8 encoded string

        :rtype: str
        """
        return self.buffer.get_text(*self.buffer.get_bounds())

    @property
    def selection(self):
        """Return buffer's selection or none as utf-8 encoded string

        :rtype: str
        """
        if self.buffer.get_has_selection():
            return self.buffer.get_text(*self.buffer.get_selection_bounds())
        else:
            None

    @property
    def uselection(self):
        """Return buffer's selection or none as unicode string

        :rtype: str
        """
        if self.buffer.get_has_selection():
            return self.selection
        else:
            None

    @property
    def utext(self):
        """Return buffer's content as unicode string

        :rtype: unicode
        """
        return unicode(self.text, 'utf-8')

    def goto_line(self, line, minimal=False):
        iterator = self.buffer.get_iter_at_line(line - 1)
        self.buffer.place_cursor(iterator)
        if minimal:
            self.view.scroll_mark_onscreen(self.buffer.get_insert())
        else:
            self.view.scroll_to_mark(self.buffer.get_insert(), 0.001, use_align=True, xalign=1.0)

    def scroll_to_cursor(self):
        self.view.scroll_to_mark(self.buffer.get_insert(), 0.001, use_align=True, xalign=1.0)

    @single_ref
    def feedback_popup(self):
        from .feedback import FeedbackPopup
        return FeedbackPopup()

    def message(self, message, timeout=1500, markup=False):
        popup = self.feedback_popup
        popup.show(self, message, timeout, markup)
        self.push_escape(popup.hide, popup.escape)

    def push_escape(self, callback, *args):
        self.push_escape_callback.emit(callback, args)

    def add_spot(self):
        self.add_spot_request.emit()

    @connect_external('view', 'move-cursor')
    def on_cursor_moved(self, view, step_size, count, extend_selection):
        if not extend_selection:
            if step_size in (gtk.MOVEMENT_PAGES, gtk.MOVEMENT_BUFFER_ENDS):
                if self.last_cursor_move is None or time.time() - self.last_cursor_move > 7:
                    self.add_spot()

                self.last_cursor_move = time.time()
            elif step_size in (gtk.MOVEMENT_VISUAL_POSITIONS, ):
                self.last_cursor_move = None

    @connect_external('buffer', 'changed')
    def on_buffer_changed(self, buffer):
        self.last_cursor_move = None

    def on_button_press_event(self, view, event):
        if event.button == 1:
            return True

        return False

    def add_widget_to_stack(self, widget, on_popup=None):
        self.stack_add_request.emit(widget, on_popup)

    def popup_widget(self, widget):
        self.stack_popup_request.emit(widget)

    def on_close(self):
        if self.buffer.get_modified():
            if 'MODIFIED_FILES' not in self.snaked_conf:
                self.snaked_conf['MODIFIED_FILES'] = {}

            self.snaked_conf['MODIFIED_FILES'][self.uri] = save_file(self.uri, self.utext,
                self.encoding, True)
        else:
            try:
                del self.snaked_conf['MODIFIED_FILES'][self.uri]
            except KeyError:
                pass
