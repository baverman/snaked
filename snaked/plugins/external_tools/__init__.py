author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'External tools'
desc = 'Allows one to define own commands'

import gtk
from uxie.utils import join_to_settings_dir

tools = []

def init(injector):
    injector.bind_menu('editor', 'external-tools', '_Run', generate_menu, resolve_menu_entry)
    injector.map_menu('Run', '<Alt>X')

def get_tools(editor):
    from parser import parse, ParseException
    if not tools:
        try:
            tools[:] = parse(open(join_to_settings_dir('snaked', 'external.tools')).read())
        except IOError:
            pass
        except ParseException, e:
            editor.message(str(e), 'error', 5000)

    return tools

def generate_menu(editor):
    has_selection = editor.buffer.get_has_selection()
    for tool in get_tools(editor):
        if tool.input == 'from-selection' and not has_selection:
            continue

        if tool.context and not all(ctx in editor.contexts for ctx in tool.context):
            continue

        yield tool.name, tool.title, (run, (editor, tool))

def resolve_menu_entry(editor, entry_id):
    for name, title, cbargs in generate_menu(editor):
        if entry_id == title:
            return cbargs + (name,)

    return None, None

def get_stdin(editor, id):
    if id == 'none' or id is None:
        return None
    elif id == 'from-buffer':
        return editor.text
    elif id == 'from-selection':
        return editor.buffer.get_text(*editor.buffer.get_selection_bounds())
    elif id == 'from-buffer-or-selection':
        if editor.buffer.get_has_selection():
            return editor.buffer.get_text(*editor.buffer.get_selection_bounds())
        else:
            return editor.text
    else:
        print 'Unknown input action', id
        editor.message('Unknown input action ' + id, 'warn')

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
    if id != 'to-feedback' and stderr:
        editor.message(stderr, 'error', 5000)

    if id == 'to-feedback':
        msg = stdout + stderr
        if not msg:
            msg = 'Empty command output'
        editor.message(msg, 'done', 5000)
    elif id == 'replace-selection':
        replace(editor, editor.buffer.get_selection_bounds(), stdout)
    elif id == 'replace-buffer':
        replace(editor, editor.buffer.get_bounds(), stdout)
    elif id == 'replace-buffer-or-selection':
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
    elif id == 'to-clipboard':
        print stdout
        clipboard = editor.view.get_clipboard(gtk.gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(stdout)
        editor.message('Command output was placed on clipboard', 'done')
    else:
        editor.message('Unknown stdout action ' + id, 'warn')

def run(editor, tool):
    import os.path
    from subprocess import Popen, PIPE
    import tempfile

    editor.message('Running ' + tool.title, 'info')

    fd, filename = tempfile.mkstemp()
    os.write(fd, tool.script)
    os.close(fd)

    stdin = get_stdin(editor, tool.input)

    command_to_run = ['/usr/bin/env', 'sh', filename]

    env = {}
    env.update(os.environ)
    env['FILENAME'] = editor.uri
    env['OFFSET'] = str(editor.cursor.get_offset())

    def on_finish():
        os.remove(filename)

    if tool.output == 'to-iconsole':
        return run_cmd_in_tty(command_to_run, editor, env, on_finish)

    proc = Popen(command_to_run, stdout=PIPE, stderr=PIPE, bufsize=1,
        stdin=PIPE if stdin else None, cwd=editor.project_root, env=env)

    if tool.output == 'to-console':
        from snaked.core.console import consume_output

        if stdin:
            proc.stdin.write(stdin)
            proc.stdin.close()

        consume_output(editor, proc, on_finish)
    else:
        stdout, stderr = proc.communicate(stdin)
        on_finish()
        process_stdout(editor, stdout, stderr, tool.output)

def run_cmd_in_tty(cmd, editor, env, on_finish):
    import pty
    from subprocess import Popen
    from snaked.core.console import consume_pty

    master, slave = pty.openpty()

    proc = Popen(cmd, stdout=slave, stderr=slave,
        stdin=slave, cwd=editor.project_root, env=env)

    consume_pty(editor, proc, master, on_finish)

def edit_external_tools(editor):
    import shutil
    from os.path import join, exists, dirname
    from snaked.util import make_missing_dirs

    filename = join_to_settings_dir('snaked', 'external.tools')
    if not exists(filename):
        make_missing_dirs(filename)
        shutil.copy(join(dirname(__file__), 'external.tools.template'), filename)

    e = editor.open_file(filename)
    e.connect('file-saved', on_external_tools_save)

def on_external_tools_save(editor):
    tools[:] = []
    editor.message('External tools updated', 'info')