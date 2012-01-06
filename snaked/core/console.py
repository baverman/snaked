import os, fcntl
import gtk
import glib
import pango

from uxie.escape import Escapable

from snaked.util import mimic_to_sourceview_theme

console_widget = []
pty_master = [None]

def init(injector):
    injector.bind('editor', 'toggle-console', 'View/Toggle _console#10',
        toggle_console).to('<alt>grave')
    injector.bind('editor-active', 'send-to-console', 'Edit/Sen_d to console#100',
        send_to_console).to('<alt>Return')

def get_console_widget(editor):
    try:
        return console_widget[0]
    except IndexError:
        pass

    w = create_console_widget()

    if editor.conf['MIMIC_PANEL_COLORS_TO_EDITOR_THEME']:
        mimic_to_sourceview_theme(w.view, editor.view)

    if editor.conf['CONSOLE_FONT']:
        w.view.modify_font(pango.FontDescription(editor.conf['CONSOLE_FONT']))

    console_widget.append(w)
    editor.window.append_panel(w)\
        .on_activate(lambda w: w.view.grab_focus())
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
    editor.window.popup_panel(console)

def unblock_fd(fd):
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
            editor.window.popup_panel(console, editor)

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
            editor.message('There is no interactive console', 'warn')
    else:
        editor.message('You need to select something', 'warn')
