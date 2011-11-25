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

    widget.entry = entry

    return widget

def hide(editor, widget):
    if widget and widget.get_parent():
        editor.widget.remove(widget)
        widget.destroy()
    editor.view.grab_focus()

def on_entry_activate(entry, editor, widget):
    filename = entry.get_text()
    if os.path.exists(filename):
        editor.message("%s already exists" % filename)
    else:
        hide(editor, widget)
        editor.window.open_or_activate(filename)

def on_entry_changed(entry, model):
    path = os.path.dirname(entry.get_text())
    if path != model.last_path:
        fill_model(model, path, entry)

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

    view.set_model(None)
    dirs = []
    files = []
    for p in os.listdir(root):
        if not next(check, False):
            return

        if p.startswith(key):
            if os.path.isdir(os.path.join(root, p)):
                dirs.append(p + '/')
            else:
                files.append(p)

    for p in sorted(dirs) + sorted(files):
        model.append((p,))

    view.set_model(model)

    completer = view.get_toplevel()
    if not len(model):
        idle(completer.popdown, entry)
    else:
        view.set_cursor((0,))
        view.get_selection().unselect_all()
        completer.set_position(entry)

def activate_func(view, path, entry, is_final):
    pos = get_pos(entry)
    root, key = get_key(entry)
    if root[-1] != '/':
        root += '/'

    if is_final:
        entry.set_text(root + view.get_model()[path][0])
        entry.set_position(-1)
        idle(entry.emit, 'changed')