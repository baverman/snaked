import weakref
import gtk
import glib

editors = weakref.WeakKeyDictionary()

def init(manager):
    """:type manager:snaked.core.plugins.ShortcutsHolder"""

    manager.add_shortcut('show-editor-list', '<alt>e', 'Window',
        'Show editor list', show_editor_list)

def editor_created(editor):
    editors[editor] = True

def editor_closed(editor):
    try:
        del editors[editor]
    except KeyError:
        pass

def create_menu(editor):
    menu = gtk.Menu()
    menu.set_reserve_toggle_size(False)
    for e in editors:
        item = gtk.MenuItem(None, True)
        title = e.get_title.emit()
        label = gtk.Label()
        label.set_alignment(0, 0.5)
        if len(title) < 15:
            label.set_width_chars(15)

        if e is editor:
            label.set_markup('<b>' + glib.markup_escape_text(title) + '</b>')
        else:
            label.set_text(title)

        item.add(label)
        menu.append(item)
        item.connect('activate', on_item_activate, weakref.ref(editor), e.uri)

    menu.show_all()

    return menu

def on_item_activate(item, editor_ref, filename):
    editor_ref().open_file(filename)

def show_editor_list(editor):
    def get_coords(menu):
        win = editor.view.get_window(gtk.TEXT_WINDOW_TEXT)
        x, y, w, h, _ = win.get_geometry()
        x, y = win.get_origin()
        mw, mh = menu.size_request()
        return x + w - mw, y + h - mh, False

    menu = create_menu(editor)
    menu.popup(None, None, get_coords, 0, gtk.get_current_event_time())
