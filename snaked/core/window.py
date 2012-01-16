import time
import weakref

import gtk

from uxie.floating import Manager as FloatingManager, TextFeedback, add_float, remove_float,\
    Feedback
from uxie.escape import Manager as EscapeManager
from uxie.actions import wait_mod_unpress_for_last_shortcut
from uxie.utils import idle, refresh_gui, lazy_func

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
        lambda e: e if e.buffer.get_has_selection() else None)
    injector.add_context('textview-active', 'window',
        lambda w: w.get_focus() if isinstance(w.get_focus(), gtk.TextView) else None)
    injector.add_context('panel-visible', 'window', Window.get_panel_visible_context)


    with injector.on('window', 'editor') as ctx:
        ctx.bind('save', 'File/_Save#20', Window.save_editor).to('<ctrl>s')

        ctx.bind('close-editor', 'Tab/_Close#100', Window.close_editor).to('<ctrl>w')
        ctx.bind('next-editor', 'Tab/_Next#50', Window.switch_to, 1).to('<ctrl>Page_Down', 1)
        ctx.bind('prev-editor', 'Tab/_Prev', Window.switch_to, -1).to('<ctrl>Page_Up', 1)
        ctx.bind('move-tab-left', 'Tab/Move to _left',
            Window.move_tab, False).to('<shift><ctrl>Page_Up', 1)
        ctx.bind('move-tab-right', 'Tab/Move to _right',
            Window.move_tab, True).to('<shift><ctrl>Page_Down', 1)

        ctx.bind('detach-editor', 'Tab/_Detach', Window.retach_editor)
        ctx.bind('duplicate-editor', 'Tab/D_uplicate', Window.duplicate_editor)

    injector.bind('editor', 'new-file', 'File/_New',
        lazy_func('snaked.core.gui.new_file.show_create_file')).to('<ctrl>n')

    with injector.on('window') as ctx:
        ctx.bind('escape', None, Window.process_escape)
        ctx.bind('close-window', 'Window/_Close#100', Window.close)

        #ctx.bind_accel('save-all', '_File/Save _all', '<ctrl><shift>s', Window.save_all)
        ctx.bind_check('fullscreen', 'Window/_Fullscreen#50', Window.toggle_fullscreen).to('F11')
        ctx.bind_check('show-tabs', 'Window/Show _Tabs', Window.show_tabs).to('<Alt>F11')

    with injector.on('panel-visible') as ctx:
        ctx.bind('increase-panel-height', 'Window/_Increase panel height',
            Window.change_panel_size, 10).to('<ctrl><alt>Up')
        ctx.bind('decrease-panel-height', 'Window/_Decrease panel height',
            Window.change_panel_size, -10).to('<ctrl><alt>Down')

class PanelHandler(object):
    def __init__(self, widget):
        self.widget = widget
        self.activate_handler = None
        self.popup_handler = None

    def on_activate(self, cb):
        self.activate_handler = cb
        return self

    def on_popup(self, cb):
        self.popup_handler = cb
        return self

    def activate(self, *args):
        if self.activate_handler:
            self.activate_handler(*((self.widget,) + args))

    def popup(self, *args):
        if self.popup_handler:
            self.popup_handler(*((self.widget,) + args))


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

    active_editor = property(get_editor_context)

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
        self.manager.editor_closed(editor)
        self.detach_editor(editor)

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
            self.manager.editor_closed(e)
            self.editors.remove(e)

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

    def on_page_removed(self, note, child, idx):
        switch_to = None
        for e in self.editors:
            if e.widget is child:
                spot = self.manager.spot_manager.get_last(None, e)
                if spot:
                    switch_to = note.page_num(spot.editor().widget)

                break

        if switch_to is None and idx > 0:
            switch_to = idx - 1

        if switch_to is not None:
            note.set_current_page(switch_to)
            refresh_gui()

        e = self.get_editor_context()
        if e:
            idle(e.view.grab_focus)

    def switch_to(self, editor, dir):
        if self.last_switch_time is None or time.time() - self.last_switch_time > 5:
            self.manager.spot_manager.add(editor)

        self.last_switch_time = time.time()

        idx = ( self.note.get_current_page() + dir ) % self.note.get_n_pages()
        self.note.set_current_page(idx)

        if not self.note.get_show_tabs() and \
                wait_mod_unpress_for_last_shortcut(self, self.hide_tab_menu):
            menu = self.get_tab_menu()

            for c in menu.get_children():
                c.deselect()

            menu.get_children()[idx].select()

    def get_tab_menu(self):
        try:
            return self.tab_menu
        except AttributeError:
            pass

        f = gtk.EventBox()

        vb = gtk.VBox()
        f.add(vb)

        for e in self.editors:
            it = gtk.MenuItem(e.get_title.emit(), False)
            vb.pack_start(it)

        add_float(self, f)
        self.tab_menu = vb
        return vb

    def hide_tab_menu(self):
        if getattr(self, 'tab_menu', None):
            remove_float(self.tab_menu.get_parent())
            del self.tab_menu

    def toggle_fullscreen(self, is_set):
        state = self.window.get_state() & gtk.gdk.WINDOW_STATE_FULLSCREEN
        if is_set:
            if state:
                self.unfullscreen()
            else:
                self.fullscreen()
        else:
            return state

    def show_tabs(self, is_set):
        if is_set:
            self.note.set_show_tabs(not self.note.get_show_tabs())
            self.window_conf['show-tabs'] = self.note.get_show_tabs()
        else:
            return self.note.get_show_tabs()

    def append_panel(self, widget):
        v = self.panels[widget] = PanelHandler(widget)
        return v

    def popup_panel(self, widget, activate=False, *args):
        if widget in self.panels:
            for w in self.panels:
                if w is not widget and w is self.main_pane.get_child2():
                    self.main_pane.remove(w)

            if not self.main_pane_position_set:
                self.main_pane_position_set = True
                _, _, _, wh, _ = self.window.get_geometry()
                self.main_pane.set_position(wh - self.window_conf.get('panel-height', 200))

            if self.main_pane.get_child2() is not widget:
                self.main_pane.add2(widget)

            if not widget.get_visible():
                widget.show()
                self.panels[widget].popup(*args)
            else:
                activate = True

            if activate:
                self.panels[widget].activate(*args)

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

    def message(self, message, category=None, timeout=None, markup=False, parent=None):
        fb = TextFeedback(message, category, markup)
        if timeout is None:
            timeout = fb.timeout
        self.push_escape(fb)
        return self.floating_manager.add(parent or self, fb, timeout=timeout)

    def feedback(self, widget, priority=None, parent=None):
        fb = Feedback(widget)
        return self.floating_manager.add(parent or self, fb, priority)

    def emessage(self, message, category=None, timeout=None, markup=False):
        fb = TextFeedback(message, category, markup)
        if timeout is None:
            timeout = fb.timeout

        e = self.get_editor_context()
        parent = e.view if e else self
        self.push_escape(fb)
        return self.floating_manager.add(parent, fb, timeout=timeout)

    def push_escape(self, obj, priority=None):
        return self.escape_manager.push(obj, priority)

    def process_escape(self):
        if not self.escape_manager.process():
            widget = self.main_pane.get_child2()
            if widget:
                if widget.get_visible():
                    if widget.get_focus_child():
                        e = self.active_editor
                        if e:
                            e.view.grab_focus()
                    else:
                        widget.hide()

                    return True

        return False

    def get_panel_visible_context(self):
        w = self.main_pane.get_child2()
        if w and w.get_visible():
            return self
        else:
            return None

    def change_panel_size(self, delta):
        self.main_pane.set_position(self.main_pane.get_position() - delta)
