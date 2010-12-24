author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Python support'
desc = 'Autocompletion, definitions navigation and smart ident'

langs = ['python']

import weakref

handlers = weakref.WeakKeyDictionary()
outline_dialog = None
test_runner = []
last_run_test = []

def init(manager):
    manager.add_shortcut('python-goto-definition', 'F3', 'Python',
        'Navigates to python definition', goto_definition)

    manager.add_shortcut('python-outline', '<ctrl>o', 'Python',
        'Opens outline dialog', open_outline)

    manager.add_shortcut('python-calltip', '<ctrl>Return', 'Python',
        'Shows calltips', show_calltips)

    manager.add_shortcut('run-test', '<ctrl>F10', 'Tests', 'Run test in cursor scope', run_test)
    manager.add_shortcut('run-all-tests', '<ctrl><shift>F10', 'Tests',
        'Run all project tests', run_all_tests)
    manager.add_shortcut('rerun-test', '<shift><alt>X', 'Tests', 'Rerun last test suite', rerun_test)
    manager.add_shortcut('toggle-test-panel', '<alt>1', 'Window',
        'Toggle test panel', toggle_test_panel)

    manager.add_global_option('PYTHON_SPYPKG_HANDLER_MAX_CHARS', 25,
        'Maximum allowed python package title length')

    manager.add_title_handler('pypkg', pypkg_handler)
    manager.add_title_handler('spypkg', spypkg_handler)

    from snaked.core.prefs import register_dialog
    register_dialog('Rope hints', edit_rope_hints, 'rope', 'hints')
    register_dialog('Rope config', edit_rope_config, 'rope', 'config')


def editor_created(editor):
    editor.connect('get-project-larva', on_editor_get_project_larva)

def editor_opened(editor):
    from plugin import Plugin
    h = Plugin(editor)
    handlers[editor] = h

def editor_closed(editor):
    try:
        del handlers[editor]
    except KeyError:
        pass

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

def get_package_root(module_path):
    import os.path

    packages = [os.path.basename(module_path).rpartition('.')[0]]
    while True:
        path = os.path.dirname(module_path)
        if path == module_path:
            break

        module_path = path

        if os.path.exists(os.path.join(module_path, '__init__.py')):
            packages.append(os.path.basename(module_path))
        else:
            break

    return module_path, '.'.join(reversed(packages))

def on_editor_get_project_larva(editor):
    from snaked.util import join_to_file_dir
    import os.path

    if os.path.exists(join_to_file_dir(editor.uri, '__init__.py')):
        editor.get_project_larva.stop_emission()
        root, packages = get_package_root(editor.uri)
        return os.path.join(root, packages.partition('.')[0])

def pypkg_handler(editor):
    uri = editor.uri
    if not uri.endswith('.py'):
        return None

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

def spypkg_handler(editor):
    package = pypkg_handler(editor)
    if not package:
        return None

    import re

    max_chars_in_title = editor.snaked_conf['PYTHON_SPYPKG_HANDLER_MAX_CHARS']

    parts = package.split('.')
    if parts < 3 or len(package) <= max_chars_in_title:
        return package

    index = len(parts) - 2
    while len(package) > max_chars_in_title:
        parts[index] = '.'
        index -= 1
        package = '.'.join(parts)
        package = re.sub(r'\.{4,}', '...', package)

        if index == 0:
            break

    return package

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

    if not editor.project_root:
        editor.message('Can not determine current project.\n'
            'Are you editing read-only file?\n'
            'Also check existence of .snaked_project directory', 8000)
        return

    ropehints = join(editor.project_root, '.ropeproject', 'ropehints.py')
    if not exists(ropehints):
        make_missing_dirs(ropehints)
        shutil.copy(join(dirname(__file__), 'ropehints_tpl.py'), ropehints)

    editor.open_file(ropehints)

def edit_rope_config(editor):
    from os.path import join, exists

    if not editor.project_root:
        editor.message('Can not determine current project.\n'
            'Are you editing read-only file?\n'
            'Also check existence of .snaked_project directory', 8000)
        return

    ropeconfig = join(editor.project_root, '.ropeproject', 'config.py')

    if exists(ropeconfig):
        editor.open_file(ropeconfig)
    else:
        if editor in handlers:
            handlers[editor].project_manager

        if exists(ropeconfig):
            editor.open_file(ropeconfig)
        else:
            editor.message('There is no existing rope config.\n'
                'Are you sure this is python project?\n'
                'Try to open any python file', 8000)

def get_pytest_runner(editor):
    """:rtype: snaked.plugins.python.pytest_runner.TestRunner()"""
    try:
        return test_runner[0]
    except IndexError:
        pass

    from pytest_runner import TestRunner
    test_runner.append(TestRunner())

    editor.add_widget_to_stack(test_runner[0].panel, test_runner[0].on_popup)
    return test_runner[0]

def toggle_test_panel(editor):
    runner = get_pytest_runner(editor)
    if runner.panel.get_focus_child():
        runner.hide()
        editor.view.grab_focus()
    else:
        runner.editor_ref = weakref.ref(editor)
        editor.popup_widget(runner.panel)
        runner.tests_view.grab_focus()

def pytest_available(editor):
    try:
        import pytest
    except ImportError:
        editor.message('You need installed pytest\nsudo pip install pytest')
        return False

    return True

def set_last_run_test(func_name, filenames):
    if last_run_test:
        last_run_test[0] = func_name, filenames
    else:
        last_run_test.append((func_name, filenames))

def run_all_tests(editor):
    if pytest_available(editor):
        editor.message('Collecting tests...')
        set_last_run_test('', [])
        get_pytest_runner(editor).run(editor)

def run_test(editor):
    if pytest_available(editor):
        filename, func_name = handlers[editor].get_scope()
        if filename:
            editor.message('Collecting tests...')
            set_last_run_test(func_name, [filename])
            get_pytest_runner(editor).run(editor, func_name, [filename])
        else:
            editor.message('Test scope can not be defined')

def rerun_test(editor):
    if pytest_available(editor):
        if last_run_test:
            editor.message('Collecting tests...')
            get_pytest_runner(editor).run(editor, *last_run_test[0])
        else:
            editor.message('You do not run any test yet')
