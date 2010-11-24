author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Python support'
desc = 'Autocompletion, definitions navigation and smart ident'

langs = ['python']

import weakref

handlers = weakref.WeakKeyDictionary()
outline_dialog = None

def init(manager):
    manager.add_shortcut('python-goto-definition', 'F3', 'Python',
        'Navigates to python definition', goto_definition)

    manager.add_shortcut('python-outline', '<ctrl>o', 'Python',
        'Opens outline dialog', open_outline)

    manager.add_shortcut('python-calltip', '<ctrl>Return', 'Python',
        'Shows calltips', show_calltips)

    from snaked.core.prefs import register_dialog
    register_dialog('Rope hints', edit_rope_hints, 'rope', 'hints')
    register_dialog('Rope config', edit_rope_config, 'rope', 'config')

def editor_created(editor):
    editor.connect('get-title', on_editor_get_title)

def editor_opened(editor):
    from plugin import Plugin
    h = Plugin(editor)
    handlers[editor] = h

def editor_closed(editor):
    del handlers[editor]

def quit():
    global outline_dialog
    if outline_dialog:
        outline_dialog.window.destroy()
        del outline_dialog

    import plugin
    for v in plugin.project_managers.values():
        v.close()

def goto_definition(editor):
    try:
        h = handlers[editor]
    except KeyError:
        return

    h.goto_definition()

def show_calltips(editor):
    try:
        h = handlers[editor]
    except KeyError:
        return

    h.show_calltips()

def on_editor_get_title(editor):
    if editor.uri.endswith('.py'):
        return get_python_title(editor.uri)

    return None

def get_python_title(uri):
    from os.path import dirname, basename, exists, join

    title = basename(uri)
    packages = []
    while True:
        path = dirname(uri)
        if path == uri:
            break

        uri = path

        if exists(join(uri, '__init__.py')):
            packages.append(basename(uri))
        else:
            break

    if packages:
        if title != '__init__.py':
            packages.insert(0, title.partition('.py')[0])

        return '.'.join(reversed(packages))
    else:
        return None

def open_outline(editor):
    global outline_dialog
    if not outline_dialog:
        from outline import OutlineDialog
        outline_dialog = OutlineDialog()

    outline_dialog.show(editor)

def edit_rope_hints(editor):
    import shutil
    from os.path import join, exists, dirname
    from snaked.util import make_missing_dirs

    ropehints = join(editor.project_root, '.ropeproject', 'ropehints.py')
    if not exists(ropehints):
        make_missing_dirs(ropehints)
        shutil.copy(join(dirname(__file__), 'ropehints_tpl.py'), ropehints)

    editor.open_file(ropehints)

def edit_rope_config(editor):
    from os.path import join, exists
    ropeconfig = join(editor.project_root, '.ropeproject', 'config.py')
    if exists(ropeconfig):
        editor.open_file(ropeconfig)
    else:
        editor.message('There is no existing rope config.\n'
            'Try to autocomplete something. Then repeat', 5000)
