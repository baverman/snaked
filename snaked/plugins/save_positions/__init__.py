author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Save positions'
desc = 'Remembers last edit position for every edited file'

prefs = {}

def init(injector):
    injector.on_ready('editor-with-new-buffer-created', editor_created)
    injector.on_done('last-buffer-editor', editor_closed)

def get_prefs(session):
    try:
        return prefs[session]
    except KeyError:
        pass

    from snaked.core.prefs import KVSettings
    p = prefs[session] = KVSettings(session, 'positions')
    return p

def editor_created(editor):
    editor.connect('get-file-position', on_editor_get_file_position)

def on_editor_get_file_position(editor):
    prefs = get_prefs(editor.session)
    if editor.uri in prefs:
        return int(prefs[editor.uri])

    return -1

def editor_closed(editor):
    prefs = get_prefs(editor.session)
    prefs[editor.uri] = str(editor.cursor.get_line())
    prefs.save()
