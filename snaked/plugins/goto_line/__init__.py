author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Goto line'
desc = 'Navigates to specified line'

import gtk

from snaked.util import idle

def init(manager):
    manager.add_shortcut('goto-line', '<ctrl>l', 'Edit', 'Goto line', goto_line)

def goto_line(editor):
    widget = get_widget(editor)
    
    editor.widget.pack_start(widget, False)
    widget.entry.grab_focus()
    widget.show_all()

def get_widget(editor):
    widget = gtk.HBox(False, 0)
    
    label = gtk.Label()
    label.set_text('Goto line:')
    widget.pack_start(label, False)
    
    entry = gtk.Entry()
    widget.pack_start(entry, False)
    entry.connect('activate', on_entry_activate, editor, widget)
    entry.connect('focus-out-event', on_focus_out, editor, widget)
    entry.connect('key-press-event', on_key_press, editor, widget)
    
    widget.entry = entry
    
    return widget
    
def hide(editor, widget):
    if widget and widget.get_parent():
        editor.widget.remove(widget)
        widget.destroy()
    editor.view.grab_focus()

def on_focus_out(sender, event, editor, widget):
    idle(hide, editor, widget)
    
def on_entry_activate(sender, editor, widget):
    idle(hide, editor, widget)
    try:
        line = int(sender.get_text())
        editor.add_spot()
        idle(editor.goto_line, line)
    except ValueError:
        pass

def on_key_press(sender, event, editor, widget):
    if event.keyval == gtk.keysyms.Escape:
        idle(hide, editor, widget)
        return True
    
    return False