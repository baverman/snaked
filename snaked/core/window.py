import time
import weakref

import gtk

from uxie.floating import Manager as FloatingManager, TextFeedback, add_float, remove_float, allocate_float
from uxie.escape import Manager as EscapeManager
from uxie.actions import wait_mod_unpress_for_last_shortcut
from uxie.utils import idle

tab_bar_pos_mapping = {
    'top': gtk.POS_TOP,
    'bottom': gtk.POS_BOTTOM,
    'left': gtk.POS_LEFT,
    'right': gtk.POS_RIGHT
}

def init(injector):
    injector.add_context('editor', 'window', Window.get_editor_context)
    injector.add_context('editor-active', 'editor', lambda e: e if e.view.is_focus() else None)
    injector.add_context('editor-with-selection', 'editor-active',
        lambda e: e if e.buffer.get_has_selection else None)

    with injector.on('window', 'editor') as ctx:
        ctx.bind_accel('save', '_File/_Save', '<ctrl>s', Window.save_editor)

        ctx.bind_accel('close-editor', '_Tab/_Close', '<ctrl>w', Window.close_editor)
        ctx.bind_accel('next-editor', '_Tab/_Next', '<ctrl>Page_Down', Window.switch_to, 1, 1)
        ctx.bind_accel('prev-editor', '_Tab/_Prev', '<ctrl>Page_Up', Window.switch_to, 1, -1)
        ctx.bind_accel('move-tab-left', '_Tab/Move to _left',
            '<shift><ctrl>Page_Up', Window.move_tab, 1, False)
        ctx.bind_accel('move-tab-right', '_Tab/Move to _right',
            '<shift><ctrl>Page_Down', Window.move_tab, 1, True)

        ctx.bind('detach-editor', '_Tab/_Detach', Window.retach_editor)
        ctx.bind('duplicate-editor', '_Tab/D_uplicate', Window.duplicate_editor)

    with injector.on('window') as ctx:
        ctx.bind('escape', None, Window.process_escape)
        ctx.bind('close-window', '_Window/_Close', Window.close)

        #ctx.bind_accel('save-all', '_File/Save _all', '<ctrl><shift>s', Window.save_all)
        #ctx.bind_accel('new-file', Window.new_file_action)
        ctx.bind_accel('fullscreen', '_Window/Toggle _fullscreen', 'F11', Window.toggle_fullscreen)
        ctx.bind_accel('toggle-tabs-visibility', '_Window/Toggle ta_bs', '<Alt>F11', Window.toggle_tabs)

        #ctx.bind_accel('place-spot', self.add_spot_with_feedback)
        #ctx.bind_accel('goto-last-spot', self.goto_last_spot)
        #ctx.bind_accel('goto-next-spot', self.goto_next_prev_spot, True)
        #ctx.bind_accel('goto-prev-spot', self.goto_next_prev_spot, False)


class Window(gtk.Window):
    def __init__(self, manager, window_conf):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)

        self.editors = []
        self.last_switch_time = None
        self.panels = weakref.WeakKeyDictionary()

        self.set_name('SnakedWindow')
        self.set_role('Editor')
        self.connect('delete-event', self.on_delete_event)

        # set border width handling, see self.on_state_event for more details
        self.connect('window-state-event', self.on_state_event)

        self.set_default_size(800, 500)

        manager.activator.attach(self)

        self.main_pane = gtk.VPaned()
        self.main_pane_position_set = False
        self.add(self.main_pane)

        conf = manager.conf
        self.window_conf = window_conf
        self.manager = manager

        self.floating_manager = FloatingManager()
        self.escape_manager = EscapeManager()

        self.note = gtk.Notebook()
        self.note.set_show_tabs(
            conf['SHOW_TABS'] if conf['SHOW_TABS'] is not None else window_conf.get('show-tabs', True))
        self.note.set_scrollable(True)
        self.note.set_property('tab-hborder', 10)
        self.note.set_property('homogeneous', False)
        self.note.set_show_border(False)
        self.note.connect_after('switch-page', self.on_switch_page)
        self.note.connect('page_removed', self.on_page_removed)
        self.note.connect('page_reordered', self.on_page_reordered)
        self.note.props.tab_pos = tab_bar_pos_mapping.get(conf['TAB_BAR_PLACEMENT'], gtk.POS_TOP)
        self.main_pane.add1(self.note)

        if conf['RESTORE_POSITION'] and 'last-position' in window_conf:
            try:
                pos, size = window_conf['last-position']
            except ValueError:
                if window_conf['last-position'] == 'fullscreen':
                    self.fullscreen()
                elif window_conf['last-position'] == 'maximized':
                    self.maximize()
            else:
                self.move(*pos)
                self.resize(*size)

        self.show_all()

    def get_editor_context(self):
        widget = self.note.get_nth_page(self.note.get_current_page())
        for e in self.editors:
            if e.widget is widget:
                return e

        return None

    def attach_editor(self, editor):
        self.editors.append(editor)
        label = gtk.Label('Unknown')
        self.note.append_page(editor.widget, label)
        self.note.set_tab_reorderable(editor.widget, True)
        self.focus_editor(editor)
        editor.view.grab_focus()

    def focus_editor(self, editor):
        idx = self.note.page_num(editor.widget)
        self.note.set_current_page(idx)

    def update_top_level_title(self):
        idx = self.note.get_current_page()
        if idx < 0:
            return

        editor = self.get_editor_context()
        if editor:
            title = editor.get_window_title.emit()

        if not title:
            title = self.note.get_tab_label_text(self.note.get_nth_page(idx))

        if title is not None:
            self.set_title(title)

    def set_editor_title(self, editor, title):
        self.note.set_tab_label_text(editor.widget, title)
        if self.note.get_current_page() == self.note.page_num(editor.widget):
            self.update_top_level_title()

    def on_delete_event(self, *args):
        self.close()

    def on_state_event(self, widget, event):
        """Sets the window border depending on state

        The window border eases the resizing of the window using the mouse.
        In maximized and fullscreen state the this use case is irrelevant.
        Removing the border in this cases makes it easier to hit the scrollbar.

        Unfortunately this currently only works with tabs hidden.
        """
        state = event.new_window_state
        if state & gtk.gdk.WINDOW_STATE_MAXIMIZED or state & gtk.gdk.WINDOW_STATE_FULLSCREEN:
            self.set_border_width(0)
        else:
            self.set_border_width(self.manager.conf['WINDOW_BORDER_WIDTH'])

    def detach_editor(self, editor):
        idx = self.note.page_num(editor.widget)
        self.note.remove_page(idx)
        self.editors.remove(editor)

    def close_editor(self, editor):
        self.detach_editor(editor)
        editor.on_close()
        self.manager.editor_closed(editor)

        if not self.editors:
            self.close()

    def close(self, notify_manager=True):
        current_editor = self.get_editor_context()
        if current_editor:
            self.window_conf['active-uri'] = current_editor.uri

        files = self.window_conf.setdefault('files', [])
        files[:] = []
        for e in self.editors[:]:
            files.append(dict(uri=e.uri))
            e.on_close()
            self.editors.remove(e)
            self.manager.editor_closed(e)

        state = self.window.get_state()
        if state & gtk.gdk.WINDOW_STATE_FULLSCREEN:
            self.window_conf['last-position'] = 'fullscreen'
        elif state & gtk.gdk.WINDOW_STATE_MAXIMIZED:
            self.window_conf['last-position'] = 'maximized'
        else:
            self.window_conf['last-position'] = self.get_position(), self.get_size()

        if self.main_pane_position_set:
            _, _, _, wh, _ = self.window.get_geometry()
            self.window_conf['panel-height'] = wh - self.main_pane.get_position()

        if notify_manager:
            self.manager.window_closed(self)

    def save(self, editor):
        editor.save()

    def on_switch_page(self, *args):
        self.update_top_level_title()

        if getattr(self, 'tab_menu', None):
            self.tab_menu.get_parent().window.show()

    def on_page_removed(self, note, child, idx):
        for e in self.editors:
            if e.widget is child:
                spot = self.manager.get_last_spot(None, e)
                if spot:
                    note.set_current_page(note.page_num(spot.editor().widget))
                    return

        if idx > 0:
            note.set_current_page(idx - 1)

    def switch_to(self, editor, dir):
        if self.last_switch_time is None or time.time() - self.last_switch_time > 5:
            self.manager.add_spot(editor)

        self.last_switch_time = time.time()

        idx = ( self.note.get_current_page() + dir ) % self.note.get_n_pages()
        self.note.set_current_page(idx)

        if not self.note.get_show_tabs():
            menu = self.get_tab_menu()

            for c in menu.get_children():
                c.deselect()

            menu.get_children()[idx].select()

            wait_mod_unpress_for_last_shortcut(self, self.hide_tab_menu)

    def get_tab_menu(self):
        try:
            return self.tab_menu
        except AttributeError:
            pass

        f = gtk.EventBox()

        vb = gtk.VBox()
        f.add(vb)

        for e in self.editors:
            it = gtk.MenuItem(e.get_title.emit())
            vb.pack_start(it)

        #def get_coords(menu):
        #    win = self.window
        #    x, y, w, h, _ = win.get_geometry()
        #    x, y = win.get_origin()
        #    mw, mh = menu.size_request()
        #    return x + w - mw, y + h - mh, False
        #
        #self.tab_menu.show_all()
        #self.tab_menu.popup(None, None, get_coords, 1, gtk.get_current_event_time())

        add_float(self, f)
        self.tab_menu = vb
        return vb

    def hide_tab_menu(self):
        if getattr(self, 'tab_menu', None):
            remove_float(self.tab_menu.get_parent())
            del self.tab_menu

    def toggle_fullscreen(self):
        if self.window.get_state() & gtk.gdk.WINDOW_STATE_FULLSCREEN:
            self.unfullscreen()
        else:
            self.fullscreen()

    def toggle_tabs(self):
        self.note.set_show_tabs(not self.note.get_show_tabs())
        self.window_conf['show-tabs'] = self.note.get_show_tabs()

    def append_panel(self, widget, on_popup):
        self.panels[widget] = on_popup

    def popup_panel(self, widget, *args):
        if widget in self.panels:
            for w in self.panels:
                if w is not widget and w is self.main_pane.get_child2():
                    self.main_pane.remove(w)

            if not self.main_pane_position_set:
                self.main_pane_position_set = True
                _, _, _, wh, _ = self.window.get_geometry()
                self.main_pane.set_position(wh - self.window_conf.get('panel-height', 200))

            self.main_pane.add2(widget)
            widget.show()

            if self.panels[widget]:
                self.panels[widget](widget, *args)

    def on_page_reordered(self, note, child, num):
        for i, e in enumerate(self.editors):
            if e.widget is child:
                self.editors[i], self.editors[num] = self.editors[num], self.editors[i]
                break

    def move_tab(self, editor, is_right):
        pos = self.note.page_num(editor.widget)
        if is_right:
            pos += 1
        else:
            pos -= 1

        if pos < 0 or pos >= self.note.get_n_pages():
            editor.message('This is dead end')
            return

        self.note.reorder_child(editor.widget, pos)

    def activate_main_window(self):
        self.present()
        #self.present_with_time(gtk.get_current_event_time())

    def retach_editor(self, editor):
        self.detach_editor(editor)
        self.manager.get_free_window().attach_editor(editor)

    def duplicate_editor(self, editor):
        self.manager.get_free_window().attach_editor(self.manager.open(editor.uri))

    def save_editor(self, editor):
        editor.save()

    def open_or_activate(self, uri, line=None):
        return self.manager.open_or_activate(uri, self, line)

    def message(self, message, category=None, timeout=None, parent=None):
        fb = TextFeedback(message, category)
        timeout = timeout or fb.timeout
        self.push_escape(fb)
        return self.floating_manager.add(parent or self, fb, 5, timeout)

    def emessage(self, message, category=None, timeout=None):
        fb = TextFeedback(message, category)
        timeout = timeout or fb.timeout

        e = self.get_editor_context()
        parent = e.view if e else self
        return self.floating_manager.add(parent, fb, 5, timeout)

    def push_escape(self, obj):
        return self.escape_manager.push(obj)

    def process_escape(self):
        self.escape_manager.process()