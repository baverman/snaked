import gtk

class Escape(object): pass
repl_widget = []

def init(manager):
    manager.add_shortcut('python-repl', '<alt>2', 'Window',
        'Toggle python interactive repl', toggle_repl)

def get_repl_widget(editor):
    try:
        return repl_widget[0]
    except IndexError:
        pass

    w = create_repl_widget()
    repl_widget.append(w)

    editor.add_widget_to_stack(w, on_repl_popup)
    return w

def create_repl_widget():
    panel = gtk.ScrolledWindow()
    panel.set_border_width(5)
    panel.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

    panel.view = gtk.TextView()
    panel.view.set_buffer(gtk.TextBuffer())
    panel.add(panel.view)
    panel.view.show()

    return panel

def toggle_repl(editor):
    repl = get_repl_widget(editor)

    if repl.get_focus_child():
        repl.hide()
        editor.view.grab_focus()
    else:
        editor.popup_widget(repl)

def hide(editor, widget, escape):
    widget.hide()
    editor.view.grab_focus()

def on_repl_popup(widget, editor):
    widget.escape = Escape()
    editor.push_escape(hide, widget, widget.escape)
    widget.view.grab_focus()
