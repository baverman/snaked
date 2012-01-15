import os.path
import gtk

from uxie.utils import idle
from uxie.escape import Escapable
from uxie.complete import EntryCompleter, create_simple_complete_view

def show_create_file(editor):
    widget = create_widget(editor)

    editor.widget.pack_start(widget, False)
    widget.entry.grab_focus()
    widget.entry.set_position(-1)
    widget.show_all()

    editor.window.push_escape(Escapable(hide, editor, widget))

def create_widget(editor):
    widget = gtk.HBox(False, 10)

    label = gtk.Label("File name:")
    widget.pack_start(label, False)

    entry = gtk.Entry()
    entry.set_width_chars(50)
    widget.pack_start(entry, False)
    entry.connect('activate', on_entry_activate, editor, widget)

    path = os.path.dirname(editor.uri)
    entry.set_text(path + '/')

    widget.completion = EntryCompleter(create_simple_complete_view())
    widget.completion.attach(entry, fill_func, activate_func)
    widget.completion.pass_enter_key = True

    widget.entry = entry

    return widget

def hide(editor, widget):
    if widget and widget.get_parent():
        editor.widget.remove(widget)
        widget.destroy()
    editor.view.grab_focus()

def on_entry_activate(entry, editor, widget):
    filename = entry.get_text()
    hide(editor, widget)
    editor.window.open_or_activate(filename)

def get_pos(entry):
    try:
        start, end = entry.get_selection_bounds()
    except ValueError:
        start = entry.get_position()

    return start

def get_key(entry):
    return os.path.split(entry.get_text()[:get_pos(entry)])

def fill_func(view, entry, check):
    root, key = get_key(entry)
    model = view.get_model()
    model.clear()

    dirs = []
    files = []
    try:
        for p in os.listdir(root):
            next(check)

            if p.startswith(key):
                if os.path.isdir(os.path.join(root, p)):
                    dirs.append(p + '/')
                else:
                    files.append(p)
    except OSError:
        pass

    for p in sorted(dirs) + sorted(files):
        model.append((p,))

    #view.get_selection().unselect_all()

def activate_func(view, path, entry, is_final):
    if is_final:
        pos = get_pos(entry)
        root, key = get_key(entry)
        if root[-1] != '/':
            root += '/'

        entry.set_text(root + view.get_model()[path][0])
        entry.set_position(-1)
        idle(entry.emit, 'changed')