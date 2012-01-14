import tempfile
import os, pty
import shutil
import gtk

from os.path import join, exists, dirname
from subprocess import Popen, PIPE
from inspect import cleandoc

from uxie.utils import make_missing_dirs, join_to_settings_dir

from snaked.core.console import consume_pty
from snaked.plugins.python.utils import get_executable

tools = None
tools_module = {}

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
    editor.view.window.freeze_updates()
    editor.buffer.begin_user_action()
    editor.buffer.delete(*bounds)
    editor.buffer.insert_at_cursor(text)
    editor.buffer.end_user_action()
    editor.view.window.thaw_updates()

def insert(editor, iter, text):
    editor.buffer.begin_user_action()
    editor.buffer.insert(iter, text)
    editor.buffer.end_user_action()

def process_stdout(editor, stdout, stderr, id):
    if id != 'to-feedback' and stderr:
        editor.message(stderr, 'error', 0)

    if id == 'to-feedback':
        if stdout or stderr:
            msg = '\n'.join(r for r in (stdout, stderr) if r)
        else:
            msg = 'Empty command output'
        editor.message(msg, 'done')
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
        clipboard = editor.view.get_clipboard(gtk.gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(stdout)
        editor.message('Command output was placed on clipboard', 'done')
    elif id == 'to-console':
        if stdout:
            from snaked.core.console import get_console_widget
            console = get_console_widget(editor)
            if not console.props.visible:
                editor.window.popup_panel(console, editor)

            buf = console.view.get_buffer()
            buf.set_text(stdout)
            buf.place_cursor(buf.get_bounds()[1])
            console.view.scroll_mark_onscreen(buf.get_insert())
    else:
        editor.message('Unknown stdout action ' + id, 'warn')

def run(editor, tool):
    if tool._callable:
        run_as_python_func(editor, tool)
    else:
        run_as_command(editor, tool)

def run_as_python_func(editor, tool):
    stdin = get_stdin(editor, tool._input)
    if stdin:
        stdin = stdin.decode('utf-8')

    stderr = stdout = None

    try:
        stdout = tool._callable(editor, stdin)
    except:
        import traceback
        stderr = traceback.format_exc()

    stdout = stdout or ''
    stderr = stderr or ''
    process_stdout(editor, stdout, stderr, tool._output)

def run_as_command(editor, tool):
    editor.message('Running ' + tool._title, 'info')

    fd, filename = tempfile.mkstemp()
    os.write(fd, tool._script)
    os.close(fd)

    stdin = get_stdin(editor, tool._input)

    command_to_run = ['/usr/bin/env', 'sh', filename]

    env = {}
    env.update(os.environ)
    env['FILENAME'] = editor.uri
    env['OFFSET'] = str(editor.cursor.get_offset())
    env['PYTHON'] = get_executable(editor.conf)

    def on_finish():
        os.remove(filename)

    if tool._output == 'to-iconsole':
        return run_cmd_in_tty(command_to_run, editor, env, on_finish)

    if tool._output == 'to-background':
        proc = Popen(command_to_run, cwd=editor.project_root, env=env)
    else:
        proc = Popen(command_to_run, stdout=PIPE, stderr=PIPE, bufsize=1,
            stdin=PIPE if stdin else None, cwd=editor.project_root, env=env)

    if tool._output == 'to-console':
        from snaked.core.console import consume_output

        if stdin:
            proc.stdin.write(stdin)
            proc.stdin.close()

        consume_output(editor, proc, on_finish)
    elif tool._output == 'to-background':
        from threading import Thread
        def bg_run():
            proc.wait()
            on_finish()

        t = Thread(target=bg_run)
        t.daemon = True
        t.start()
    else:
        stdout, stderr = proc.communicate(stdin)
        on_finish()
        process_stdout(editor, stdout, stderr, tool._output)

def run_cmd_in_tty(cmd, editor, env, on_finish):
    master, slave = pty.openpty()

    proc = Popen(cmd, stdout=slave, stderr=slave,
        stdin=slave, cwd=editor.project_root, env=env)

    consume_pty(editor, proc, master, on_finish)

def edit_external_tools(editor, kind):
    if kind == 'global':
        filename = join_to_settings_dir('snaked', 'tools.conf')
    elif kind == 'session':
        filename = join_to_settings_dir('snaked', editor.session, 'tools')
    else:
        raise Exception('Unknown external tools type: ' + str(kind))

    if not exists(filename):
        make_missing_dirs(filename)
        shutil.copy(join(dirname(__file__), 'external.tools.template'), filename)

    e = editor.window.manager.open(filename, contexts='python')
    editor.window.attach_editor(e)
    e.connect('file-saved', on_external_tools_save)

def on_external_tools_save(editor):
    global tools
    tools = None
    editor.message('External tools updated', 'info')

def get_tools(editor):
    global tools, tool
    tools_module.clear()

    if tools is None:
        tools = []
        added_tools = set()

        filenames = (join_to_settings_dir('snaked', editor.session, 'tools'),
            join_to_settings_dir('snaked', 'tools.conf'))

        for f in filenames:
            tool = ToolExtractor()

            try:
                execfile(f, tools_module.setdefault(f, {}), tools_module.setdefault(f, {}))
            except IOError:
                pass
            except:
                import traceback
                editor.message('Unable to load ' + f + '\n\n' + traceback.format_exc(3), 'error', 0)
            else:
                for t in tool._tools:
                    if t._title in added_tools: continue
                    tools.append(t)
                    added_tools.add(t._title)

    return tools

def generate_menu(editor):
    has_selection = editor.buffer.get_has_selection()
    for tool in get_tools(editor):
        if tool._input == 'from-selection' and not has_selection:
            continue

        if tool._context and not all(ctx in editor.contexts for ctx in tool._context):
            continue

        yield tool._name, tool._title, (run, (editor, tool))

def resolve_menu_entry(editor, entry_id):
    for name, title, cbargs in generate_menu(editor):
        if entry_id == title:
            return cbargs + (name,)

    return None, None, None

allowed_inputs = ('from_buffer_or_selection', 'from_buffer', 'from_selection')
allowed_outputs = ('replace_buffer_or_selection', 'replace_buffer', 'replace_selection',
    'to_console', 'to_iconsole', 'to_feedback', 'to_clipboard', 'insert', 'insert_at_end',
    'to_background')

class ToolExtractor(object):
    def __init__(self):
        self._tools = []

        fake_tool = Tool()
        self.from_buffer_or_selection = fake_tool
        self.from_buffer = fake_tool
        self.from_selection = fake_tool
        self.replace_buffer_or_selection = fake_tool
        self.replace_buffer = fake_tool
        self.replace_selection = fake_tool
        self.to_console = fake_tool
        self.to_iconsole = fake_tool
        self.to_feedback = fake_tool
        self.to_clipboard = fake_tool
        self.to_background = fake_tool
        self.insert = fake_tool
        self.insert_at_end = fake_tool

    def __getattribute__(self, name):
        if name in allowed_inputs + allowed_outputs + ('__call__', 'when'):
            t = Tool()
            self._tools.append(t)
            return getattr(t, name)

        return object.__getattribute__(self, name)

    def __call__(self, *args):
        t = Tool()
        self._tools.append(t)
        return t(*args)

    def when(_self, *ctx):
        return Tool().when(*ctx)


class Tool(object):
    def __init__(self):
        self._name = None
        self._input = None
        self._output = 'to-console'
        self._context = None
        self._script = None
        self._callable = None

        self.from_buffer_or_selection = self
        self.from_buffer = self
        self.from_selection = self
        self.replace_buffer_or_selection = self
        self.replace_buffer = self
        self.replace_selection = self
        self.to_console = self
        self.to_iconsole = self
        self.to_feedback = self
        self.to_clipboard = self
        self.to_background = self
        self.insert = self
        self.insert_at_end = self

    @property
    def _title(self):
        return self._name.replace('_', '')

    def __getattribute__(self, name):
        if name in allowed_inputs:
            self._input = name.replace('_', '-')
        elif name in allowed_outputs:
            self._output = name.replace('_', '-')

        return object.__getattribute__(self, name)

    def when(self, *ctx):
        self._context = ctx
        return self

    def __call__(self, *args):
        if not args:
            return self._handle_arg

        assert len(args) == 1
        arg = args[0]
        if not self._name and not callable(arg):
            assert '\n' not in arg
            self._name = arg
            return self

        self._handle_arg(arg)

    def _handle_arg(self, callable_or_script):
        if callable(callable_or_script):
            self._callable = callable_or_script
            if not self._name:
                self._name = self._callable.__name__.replace('___', '###').replace(
                    '__', '%%%').replace('_', ' ').replace('###', ' _').replace('%%%', '_')
        else:
            self._script = cleandoc(callable_or_script)

tool = ToolExtractor()
