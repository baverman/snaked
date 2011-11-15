import os.path
import weakref

import gtk
import gtksourceview2

from uxie.utils import idle

from .prefs import add_option, update_view_preferences
from ..util import save_file, get_project_root
from ..signals import SignalManager, Signal, connect_all, connect_external, weak_connect

add_option('DISABLE_LEFT_CLICK', False, 'Disable left mouse button handling in editor view')

class Editor(SignalManager):
    before_close = Signal()
    before_file_save = Signal(return_type=bool) # Handlers can return True to prevent file saving

    file_loaded = Signal()
    file_saved = Signal()

    get_file_position = Signal(return_type=int)
    get_project_larva = Signal(return_type=str)
    get_title = Signal(return_type=str)
    get_window_title = Signal(return_type=str)

    def __init__(self, conf, buf=None):
        self.last_cursor_move = None

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)

        self.buffer = buf or gtksourceview2.Buffer()

        self.view = gtksourceview2.View()
        self.view.set_buffer(self.buffer)
        sw.add(self.view)
        self.view.editor_ref = weakref.ref(self)

        self.ins_mark = self.sb_mark = None
        self.view.connect('focus-in-event', self.on_focus_in)
        self.view.connect('focus-out-event', self.on_focus_out)

        self.widget = gtk.VBox(False, 0)
        self.widget.pack_start(sw)

        self.widget.show_all()

        connect_all(self, buffer=self.buffer, view=self.view)

        if conf['DISABLE_LEFT_CLICK']:
            weak_connect(self.view, 'button-press-event', self, 'on_button_press_event')

        self.conf = conf

        if buf:
            idle(self.update_view_preferences)
            idle(self.update_title)

    def update_title(self):
        if self.uri:
            title = self.get_title.emit()

            if not title:
                title = os.path.basename(self.uri)
        else:
            title = 'Unknown'

        self.window.set_editor_title(self, title)

    @property
    def uri(self):
        return self.buffer.uri

    @property
    def encoding(self):
        return self.buffer.encoding

    @property
    def session(self):
        return self.buffer.session

    def load_file(self, filename, line=None):
        self.buffer.uri = os.path.abspath(filename)
        self.buffer.encoding = 'utf-8'
        self.buffer.saveable = True

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
                        self.buffer.encoding = result['encoding']
                        idle(self.message,
                            'Automatically selected ' + self.buffer.encoding + 'encoding', 'info', 5000)
                    else:
                        self.buffer.saveable = False
                        utext = 'Is this a text file?'
                except ImportError:
                    self.buffer.saveable = False
                    utext = str(e)
                except UnicodeDecodeError, ee:
                    self.buffer.saveable = False
                    utext = str(ee)

            self.buffer.set_text(utext)
            self.buffer.set_modified(False)

            self.buffer.end_not_undoable_action()

            if self.uri in self.conf['MODIFIED_FILES']:
                tmpfilename = self.conf['MODIFIED_FILES'][self.uri]
                if os.path.exists(tmpfilename):
                    self.buffer.begin_user_action()
                    utext = open(tmpfilename).read().decode(self.buffer.encoding)
                    self.buffer.set_text(utext)
                    self.buffer.end_user_action()

            self.on_modified_changed_handler.unblock()
            self.view.window.thaw_updates()
            self.buffer.is_changed = False

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
        if not self.buffer.saveable:
            self.message("This file was opened with error and can't be saved", 'warn')
            return

        if self.uri:
            if self.before_file_save.emit():
                return

            if self.buffer.config['remove-trailing-space']:
                from snaked.core.processors import remove_trailing_spaces
                remove_trailing_spaces(self.buffer)

            # TODO quick hack to ignore file changes by snaked itself
            try:
                save_file(self.uri, self.utext, self.encoding)
                self.buffer.monitor.saved_by_snaked = True
                if not self.buffer.get_modified():
                    self.message("%s saved" % self.uri, 'done')
                self.buffer.set_modified(False)
                self.file_saved.emit()
            except Exception, e:
                self.message(str(e), 'error', 5000)

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

    def clear_cursor(self):
        if self.ins_mark:
            self.buffer.delete_mark(self.ins_mark)
            self.ins_mark = None

        if self.sb_mark:
            self.buffer.delete_mark(self.sb_mark)
            self.sb_mark = None

    def goto_line(self, line, minimal=False):
        iterator = self.buffer.get_iter_at_line(line - 1)
        self.buffer.place_cursor(iterator)
        if minimal:
            self.view.scroll_mark_onscreen(self.buffer.get_insert())
        else:
            self.view.scroll_to_mark(self.buffer.get_insert(), 0.001, use_align=True, xalign=1.0)

        self.clear_cursor()

    def scroll_to_cursor(self):
        self.view.scroll_to_mark(self.buffer.get_insert(), 0.001, use_align=True, xalign=1.0)
        self.clear_cursor()

    def message(self, message, category=None, timeout=None, markup=False):
        return self.window.message(message, category, timeout, markup=markup, parent=self.view)

    def add_spot(self):
        self.window.manager.spot_manager.add(self)

    def on_button_press_event(self, view, event):
        if event.button == 1:
            return True

        return False

    def on_close(self):
        self.view.destroy()

    def update_view_preferences(self):
        update_view_preferences(self.view, self.buffer)

    @property
    def window(self):
        return self.view.get_toplevel()

    def close(self):
        self.window.close_editor(self)

    def focus(self):
        w = self.window
        w.focus_editor(self)
        w.present()

    @property
    def lang(self):
        return self.buffer.lang

    @property
    def contexts(self):
        return self.buffer.contexts

    def on_focus_in(self, view, event):
        if self.ins_mark:
            buf = self.buffer
            buf.select_range(buf.get_iter_at_mark(self.ins_mark),
                buf.get_iter_at_mark(self.sb_mark))

        return False

    def on_focus_out(self, view, event):
        buf = self.buffer
        ins = buf.get_iter_at_mark(buf.get_insert())
        sb = buf.get_iter_at_mark(buf.get_selection_bound())

        if self.ins_mark:
            buf.move_mark(self.ins_mark, ins)
        else:
            self.ins_mark = buf.create_mark(None, ins)

        if self.sb_mark:
            buf.move_mark(self.sb_mark, sb)
        else:
            self.sb_mark = buf.create_mark(None, sb)