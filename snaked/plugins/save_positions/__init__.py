author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Save positions'
desc = 'Remembers last edit position for every edited file'

prefs = None

def get_prefs():
    global prefs
    if not prefs:
        from snaked.core.prefs import KVSettings
        prefs = KVSettings('positions.db')
    
    return prefs

def editor_created(editor):
    editor.connect('get-file-position', on_editor_get_file_position)

def on_editor_get_file_position(editor):
    prefs = get_prefs()
    if editor.uri in prefs:
        return int(prefs[editor.uri])
    
    return -1

def editor_closed(editor):
    prefs = get_prefs()
    prefs[editor.uri] = str(editor.cursor.get_line())

def quit():
    global prefs
    if prefs:
        del prefs
