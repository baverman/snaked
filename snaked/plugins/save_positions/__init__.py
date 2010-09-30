prefs = None

def get_prefs():
    global prefs
    if not prefs:
        from snaked.core.prefs import KVSettings
        prefs = KVSettings('positions.db')
    
    return prefs

def editor_opened(editor):
    prefs = get_prefs()
    
    if editor.uri in prefs:
        from snaked.util import refresh_gui
        refresh_gui()
        iterator = editor.buffer.get_iter_at_line(int(prefs[editor.uri]))
        editor.buffer.place_cursor(iterator)
        editor.view.scroll_to_iter(iterator, 0.001, use_align=True, xalign=1.0)

def editor_closed(editor):
    prefs = get_prefs()
    prefs[editor.uri] = str(editor.cursor.get_line())

def quit():
    global prefs
    if prefs:
        del prefs
