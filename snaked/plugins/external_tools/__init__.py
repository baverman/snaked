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

def get_run_menu(prefs, editor):
    menu = gtk.Menu()
    menu.set_reserve_toggle_size(False)

    for tool in sorted(prefs):
        item = gtk.MenuItem(None, True)
        label = gtk.Label()
        label.set_alignment(0, 0.5)
        label.set_width_chars(10)
        label.set_markup_with_mnemonic(prefs[tool]['name'])
        item.add(label)
        item.run_prefs = prefs[tool]
        menu.append(item)

    menu.connect_after('activate-current', on_menu_activate)
    menu.show_all()
    return menu
    
def run_tool(editor):
    from snaked.core.prefs import load_json_settings
    
    prefs = load_json_settings('external-tools.conf', {})
    if not prefs:
        editor.message('There is no any tool to run')
        return

    def get_coords(menu):
        r = editor.view.get_iter_location(editor.cursor)
        x, y = editor.view.buffer_to_window_coords(gtk.TEXT_WINDOW_WIDGET, r.x, r.y)
        dx, dy = editor.view.get_window(gtk.TEXT_WINDOW_WIDGET).get_origin()
        return x+dx, y+dy, False

    menu = get_run_menu(prefs, editor)
    menu.editor = weakref.ref(editor)
    menu.popup(None, None, get_coords, 0, gtk.get_current_event_time())

def on_menu_activate(menu, *args):
    idle(run, menu.editor(), menu.get_active().run_prefs)
    idle(menu.destroy)

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
    editor.buffer.begin_user_action()
    editor.buffer.delete(*bounds)
    editor.buffer.insert_at_cursor(text)
    editor.buffer.end_user_action()

def insert(editor, iter, text):
    editor.buffer.begin_user_action()
    editor.buffer.insert(iter, text)
    editor.buffer.end_user_action()

def process_stdout(editor, stdout, id):
    if id == 'show-feedback':
        editor.message(stdout, 3000)
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

def run(editor, prefs):
    import shlex
    import os.path
    from subprocess import Popen, PIPE
    
    command = shlex.split(prefs['command'])
    if not command:
        editor.message('Tool must define command to run')
        return    

    editor.message('Running ' + prefs['name'])

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
        
    if stderr:
        editor.message(stderr, 5000)
        
    process_stdout(editor, stdout, prefs['stdout'])