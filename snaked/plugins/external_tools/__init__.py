author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'External tools'
desc = 'Allows one to define own commands'

import weakref
import gtk

from snaked.util import idle
from snaked.core.prefs import register_dialog

def init(manager):
    manager.add_shortcut('external-tools', '<alt>x', 'Tools', 'Run tool', run_tool)
    register_dialog('External tools', show_preferences, 'run', 'external', 'tool', 'command')

def to_str(data, encoding='utf-8'):
    if isinstance(data, unicode):
        return data.encode(encoding)

    return data

def get_run_menu(prefs, editor):
    menu = gtk.Menu()
    menu.set_reserve_toggle_size(False)

    has_selection = editor.buffer.get_has_selection()

    any_items = False
    for tool in sorted(prefs):
        if prefs[tool]['stdin'] == 'selection' and not has_selection:
            continue

        if prefs[tool]['langs'].strip() and editor.lang not in map(str.strip,
                to_str(prefs[tool]['langs']).split(',')):
            continue

        any_items = True
        item = gtk.MenuItem(None, True)
        label = gtk.Label()
        label.set_alignment(0, 0.5)
        label.set_markup_with_mnemonic(prefs[tool]['name'])
        if len(tool) < 10:
            label.set_width_chars(10)

        item.add(label)
        menu.append(item)
        item.connect('activate', on_item_activate, weakref.ref(editor), tool, prefs[tool])

    if any_items:
        menu.show_all()
        return menu
    else:
        menu.destroy()
        return None

def run_tool(editor):
    from snaked.core.prefs import load_json_settings

    prefs = load_json_settings('external-tools.conf', {})
    if not prefs:
        editor.message('There is no any tool to run')
        return

    def get_coords(menu):
        win = editor.view.get_window(gtk.TEXT_WINDOW_TEXT)
        x, y, w, h, _ = win.get_geometry()
        x, y = win.get_origin()
        mw, mh = menu.size_request()
        return x + w - mw, y + h - mh, False

    menu = get_run_menu(prefs, editor)
    if not menu:
        editor.message('There is no any tool to run')
        return

    menu.popup(None, None, get_coords, 0, gtk.get_current_event_time())

def on_item_activate(item, editor, name, prefs):
    idle(run, editor(), name, prefs)
    idle(item.get_parent().destroy)

def show_preferences(editor):
    from prefs import PreferencesDialog
    PreferencesDialog().show(editor)

def get_stdin(editor, id):
    if id == 'none':
        return None
    elif id == 'buffer':
        return editor.text
    elif id == 'selection':
        return editor.buffer.get_text(*editor.buffer.get_selection_bounds())
    elif id == 'buffer-or-selection':
        if editor.buffer.get_has_selection():
            return editor.buffer.get_text(*editor.buffer.get_selection_bounds())
        else:
            return editor.text

def replace(editor, bounds, text):
    line = editor.cursor.get_line()
    editor.view.window.freeze_updates()

    editor.buffer.begin_user_action()
    editor.buffer.delete(*bounds)
    editor.buffer.insert_at_cursor(text)
    editor.buffer.end_user_action()
    editor.goto_line(line + 1)
    editor.view.window.thaw_updates()

def insert(editor, iter, text):
    editor.buffer.begin_user_action()
    editor.buffer.insert(iter, text)
    editor.buffer.end_user_action()

def process_stdout(editor, stdout, stderr, id):
    if id != 'show-feedback' and stderr:
        editor.message(stderr, 5000)

    if id == 'show-feedback':
        msg = stdout + stderr
        if not msg:
            msg = 'Empty command output'
        editor.message(msg, 5000)
    elif id == 'replace-selection':
        replace(editor, editor.buffer.get_selection_bounds(), stdout)
    elif id == 'replace-buffer':
        replace(editor, editor.buffer.get_bounds(), stdout)
    elif id == 'replace-selection-or-buffer':
        if editor.buffer.get_has_selection():
            replace(editor, editor.buffer.get_selection_bounds(), stdout)
        else:
            replace(editor, editor.buffer.get_bounds(), stdout)
    elif id == 'insert':
        insert(editor, editor.cursor, stdout)
    elif id == 'insert-at-end':
        last_line = editor.buffer.get_line_count()
        insert(editor, editor.buffer.get_bounds()[1], stdout)
        editor.goto_line(last_line)
    elif id == 'clipboard':
        clipboard = editor.view.get_clipboard(gtk.gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(stdout)
        editor.message('Command output was placed on clipboard')
    else:
        editor.message('Unknown stdout action ' + id)

def run(editor, name, prefs):
    import shlex
    import os.path
    from subprocess import Popen, PIPE

    command = shlex.split(to_str(prefs['command']))
    if not command:
        editor.message('Tool must define command to run')
        return

    editor.message('Running ' + name)

    stdin = get_stdin(editor, prefs['stdin'])

    current_file = editor.uri
    current_dir = os.path.dirname(current_file)
    current_project = editor.project_root

    command_to_run = ['/usr/bin/env']
    for c in command:
        command_to_run.append(c.replace('%f', current_file).replace(
            '%d', current_dir).replace('%p', current_project))

    stdout, stderr = Popen(command_to_run, stdout=PIPE, stderr=PIPE,
        stdin=PIPE if stdin else None).communicate(stdin)

    process_stdout(editor, stdout, stderr, prefs['stdout'])