import os.path
import os

import gtk

def show_create_file(editor):
    widget = create_widget(editor)

    editor.widget.pack_start(widget, False)
    widget.entry.grab_focus()
    widget.entry.set_position(-1)
    widget.show_all()

    editor.push_escape(hide, widget)

def create_widget(editor):
    widget = gtk.HBox(False, 10)

    label = gtk.Label("File name:")
    widget.pack_start(label, False)

    entry = gtk.Entry()
    entry.set_width_chars(50)
    widget.pack_start(entry, False)
    entry.connect('activate', on_entry_activate, editor, widget)
    entry.connect('key-press-event', on_key_press)

    completion = gtk.EntryCompletion()
    model = gtk.ListStore(str)
    completion.set_model(model)
    completion.set_inline_completion(True)

    cell = gtk.CellRendererText()
    completion.pack_start(cell)
    completion.add_attribute(cell, 'text', 0)

    completion.set_match_func(match_func)

    entry.set_completion(completion)

    path = os.path.dirname(editor.uri)
    entry.set_text(path + '/')
    fill_model(model, path)

    entry.connect('changed', on_entry_changed, model)

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
        editor.open_file(filename)

def on_entry_changed(entry, model):
    path = os.path.dirname(entry.get_text())
    if path != model.last_path:
        fill_model(model, path, entry)

def on_key_press(sender, event):
    if event.keyval in (gtk.keysyms.ISO_Left_Tab, gtk.keysyms.Up, gtk.keysyms.Down):
        return True

    if event.keyval == gtk.keysyms.Tab:
        matches = get_matches(sender)
        if len(matches) == 1:
            sender.set_text(matches[0])
            sender.set_position(-1)
        elif len(matches) > 1:
            idx = -1
            text = sender.get_text()
            for i, m in enumerate(matches):
                if m == text:
                    idx = i
                    break

            old_pos = get_pos(sender)
            sender.handler_block_by_func(on_entry_changed)
            sender.set_text(matches[(idx + 1) % len(matches)])
            sender.set_position(old_pos)
            sender.select_region(old_pos, -1)
            sender.handler_unblock_by_func(on_entry_changed)

        return True

    return False

def get_pos(entry):
    try:
        start, end = entry.get_selection_bounds()
    except ValueError:
        start = entry.get_position()

    return start

def get_key(entry):
    return os.path.basename(entry.get_text()[:get_pos(entry)])

def match_func(completion, key, iter):
    key = get_key(completion.get_entry())
    model = completion.get_model()
    text = model.get_value(iter, 0)
    if text and text.startswith(key):
        return True

    return False

def get_matches(entry):
    model = entry.get_completion().get_model()
    key = get_key(entry)
    return sorted([os.path.join(model.last_path, text) + '/'
        for (text,) in model if text.startswith(key)])

def fill_model(model, path, entry=None):
    model.clear()
    model.last_path = path
    try:
        for p in os.listdir(path):
            fullpath = os.path.join(path, p)
            if os.path.isdir(fullpath):
                model.append((p,))
    except OSError:
        pass