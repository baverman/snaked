author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Python support'
desc = 'Autocompletion, definitions navigation and smart ident'

import weakref

handlers = weakref.WeakKeyDictionary()
outline_dialog = None
test_runner = []
last_run_test = []

def is_python_editor(editor):
    return editor.lang == 'python'

def init(injector):
    injector.add_context('python-editor', 'editor-active',
        lambda e: e if is_python_editor(e) else None)

    injector.bind('python-editor', 'goto-definition', '_Python/Goto _defenition', goto_definition)
    injector.bind('python-editor', 'show-outline', '_Python/Show _outline', open_outline)

    injector.bind('python-editor', 'show-calltip', '_Python/Show calltip', show_calltips)

    #injector.bind_accel('run-test', '<ctrl>F10', 'Tests', 'Run test in cursor scope', run_test)
    #injector.bind_accel('run-all-tests', '<ctrl><shift>F10', 'Tests',
    #    'Run all project tests', run_all_tests)
    #injector.bind_accel('rerun-test', '<shift><alt>X', 'Tests', 'Rerun last test suite', rerun_test)
    #injector.bind_accel('toggle-test-panel', '<alt>1', 'Window',
    #    'Toggle test panel', toggle_test_panel)

    from snaked.core.prefs import add_option
    add_option('PYTHON_EXECUTABLE', 'default',
        'Path to python executable. Used by test runner and completion framework')
    add_option('PYTHON_EXECUTABLE_ENV', dict,
        'Python interpreter environment. Used by test runner and completion framework')
    add_option('PYTHON_SUPP_CONFIG', dict, 'Config for supplement')

    add_option('PYTHON_SPYPKG_HANDLER_MAX_CHARS', 25, 'Maximum allowed python package title length')

    from snaked.core.titler import add_title_handler
    add_title_handler('pypkg', pypkg_handler)
    add_title_handler('spypkg', spypkg_handler)

    injector.on_ready('editor-with-new-buffer-created', editor_created)
    injector.on_ready('editor-with-new-buffer', editor_opened)
    injector.on_done('last-buffer-editor', editor_closed)
    injector.on_done('manager', quit)

def editor_created(editor):
    if is_python_editor(editor):
        editor.connect('get-project-larva', on_editor_get_project_larva)

def editor_opened(editor):
    if is_python_editor(editor):
        from plugin import Plugin
        h = Plugin(editor)
        handlers[editor] = h

def editor_closed(editor):
    try:
        del handlers[editor]
    except KeyError:
        pass

def quit(manager):
    global outline_dialog
    if outline_dialog:
        outline_dialog.window.destroy()
        del outline_dialog

    import plugin
    for v in plugin.environments.values():
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
    from uxie.utils import join_to_file_dir
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

    max_chars_in_title = editor.conf['PYTHON_SPYPKG_HANDLER_MAX_CHARS']

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

def get_pytest_runner(editor):
    """:rtype: snaked.plugins.python.pytest_runner.TestRunner()"""
    try:
        return test_runner[0]
    except IndexError:
        pass

    from pytest_runner import TestRunner
    test_runner.append(TestRunner())

    editor.window.append_panel(test_runner[0].panel, test_runner[0].on_popup)
    return test_runner[0]

def toggle_test_panel(editor):
    runner = get_pytest_runner(editor)
    if runner.panel.get_focus_child():
        runner.hide()
        editor.view.grab_focus()
    else:
        runner.editor_ref = weakref.ref(editor)
        editor.window.popup_panel(runner.panel, editor)
        runner.tests_view.grab_focus()

def pytest_available(editor):
    try:
        import pytest
    except ImportError:
        editor.message('You need installed pytest\nsudo pip install pytest', 'warn')
        return False

    return True

def set_last_run_test(*args):
    if last_run_test:
        last_run_test[0] = args
    else:
        last_run_test.append(args)

def run_all_tests(editor):
    if pytest_available(editor):
        editor.message('Collecting tests...', 'info')
        set_last_run_test(editor.project_root, '', [])
        get_pytest_runner(editor).run(editor, editor.project_root)

def run_test(editor):
    if pytest_available(editor):
        filename, func_name = handlers[editor].get_scope()
        if filename:
            editor.message('Collecting tests...', 'info')
            set_last_run_test(editor.project_root, func_name, [filename])
            get_pytest_runner(editor).run(editor, editor.project_root, func_name, [filename])
        else:
            editor.message('Test scope can not be defined', 'warn')

def rerun_test(editor):
    if pytest_available(editor):
        if last_run_test:
            editor.message('Collecting tests...', 'info')
            get_pytest_runner(editor).run(editor, *last_run_test[0])
        else:
            editor.message('You did not run any test yet', 'warn')
