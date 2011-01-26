import os
import gtk
import glib
import pango

from snaked.util import mimic_to_sourceview_theme

console_widget = []
pty_master = [None]

class Escape(object): pass

def get_console_widget(editor):
    try:
        return console_widget[0]
    except IndexError:
        pass

    w = create_console_widget()

    if editor.snaked_conf['MIMIC_PANEL_COLORS_TO_EDITOR_THEME']:
        mimic_to_sourceview_theme(w.view, editor.view)

    console_widget.append(w)

    editor.add_widget_to_stack(w, on_console_popup)
    return w

def create_console_widget():
    panel = gtk.ScrolledWindow()
    panel.set_border_width(5)
    panel.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

    panel.view = gtk.TextView()
    panel.view.set_editable(False)
    panel.view.set_buffer(gtk.TextBuffer())
    panel.add(panel.view)
    panel.view.show()

    return panel

def toggle_console(editor):
    console = get_console_widget(editor)

    if console.props.visible:
        console.hide()
        editor.view.grab_focus()
    else:
        editor.popup_widget(console)

def hide(editor, widget, escape):
    widget.hide()
    editor.view.grab_focus()

def on_console_popup(widget, editor):
    if editor.snaked_conf['CONSOLE_FONT']:
        widget.view.modify_font(pango.FontDescription(editor.snaked_conf['CONSOLE_FONT']))
    widget.escape = Escape()
    editor.push_escape(hide, widget, widget.escape)

def unblock_fd(fd):
    import fcntl, os
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

def consume_output(editor, proc, on_finish):
    console = get_console_widget(editor)
    buf = console.view.get_buffer()
    buf.delete(*buf.get_bounds())
    unblock_fd(proc.stdout)
    unblock_fd(proc.stderr)
    glib.io_add_watch(proc.stdout, glib.IO_IN|glib.IO_ERR|glib.IO_HUP,
        consume_io, editor, console, proc, on_finish)
    glib.io_add_watch(proc.stderr, glib.IO_IN|glib.IO_ERR|glib.IO_HUP,
        consume_io, editor, console, proc, on_finish)

def consume_pty(editor, proc, master, on_finish):
    console = get_console_widget(editor)
    buf = console.view.get_buffer()
    buf.delete(*buf.get_bounds())
    unblock_fd(master)
    glib.io_add_watch(master, glib.IO_IN|glib.IO_ERR|glib.IO_HUP,
        consume_io, editor, console, proc, on_finish)

    pty_master[0] = master

def consume_io(f, cond, editor, console, proc, on_finish):
    if isinstance(f, int):
        data = os.read(f, 1024)
    else:
        data = f.read()

    if data:
        if not console.props.visible:
            editor.popup_widget(console)

        buf = console.view.get_buffer()
        iter = buf.get_bounds()[1]
        buf.insert(iter, data)
        buf.place_cursor(buf.get_bounds()[1])
        console.view.scroll_mark_onscreen(buf.get_insert())

    if proc.poll() is not None:
        if not getattr(proc, 'consume_done', False):
            proc.consume_done = True
            if pty_master[0] == f:
                pty_master[0] = None
            on_finish()
        return False

    return True

def send_to_console(editor):
    selection = editor.selection
    if selection:
        if pty_master[0]:
            os.write(pty_master[0], selection)
        else:
            editor.message('There is no interactive console')
    else:
        editor.message('You need to select something')
