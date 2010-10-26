author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'External tools'
desc = 'Allows one to define own commands'

import gtk

from snaked.core.prefs import register_dialog

def init(manager):
    manager.add_shortcut('external-tools', '<alt>x', 'Tools', 'Run tool', run_tool)
    register_dialog('External tools', show_preferences, 'run', 'external', 'tool', 'command')

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
    
    menu = gtk.Menu()
    for tool in sorted(prefs):
        menu.append(gtk.MenuItem(prefs[tool]['name'], True))
    menu.show_all()        
    menu.popup(None, None, get_coords, 0, gtk.get_current_event_time())
    
def show_preferences(editor):
    from prefs import PreferencesDialog
    PreferencesDialog().show(editor)