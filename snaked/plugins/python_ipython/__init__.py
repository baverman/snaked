# -*- coding: utf-8 -*-

author = 'Gu Ye <cooyeah at gmail dot com>'
name = 'IPython console'
desc = 'IPythonView plugin for snaked editor'

import gtk
from ipython_view import IPythonView

import pango
import os


def getText(prompt='', title=''):

    def responseToDialog(entry, dialog, response):
        dialog.response(response)

    dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL
                               | gtk.DIALOG_DESTROY_WITH_PARENT,
                               gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK,
                               None)
    dialog.set_title(title)
    dialog.set_markup(title)
    entry = gtk.Entry()
    entry.connect('activate', responseToDialog, dialog, gtk.RESPONSE_OK)
    hbox = gtk.HBox()
    hbox.pack_start(gtk.Label(prompt), False, 5, 5)
    hbox.pack_end(entry)
    dialog.vbox.pack_end(hbox, True, True, 0)
    dialog.show_all()

    dialog.run()
    text = entry.get_text()
    dialog.destroy()
    return text


class SnakedIPythonView(IPythonView):

    def __init__(self):
        IPythonView.__init__(self)
        self.cout.write = self._write
        self.cout.flush = self.flush
        import __builtin__
        __builtin__.raw_input = self._raw_input

        self.last_run_command = None

    def _write(self, txt):
        self.write(txt)
        self.flush()

    def flush(self):
        rv = self.cout.getvalue()
        if rv:
            self.write(rv)
            self.cout.truncate(0)
            while gtk.events_pending():
                gtk.main_iteration_do(False)

    def _raw_input(self, prompt=''):
        title = ''
        if prompt == 'ipdb> ':
            title = 'Input pdb command'
        return getText(prompt=prompt, title=title)

    def commandProcessed(self, cmd):
        cmd = cmd.strip()
        if cmd.startswith('run ') or cmd.startswith('%run '):
            self.last_run_command = cmd


class IPythonRunner:

    def __init__(self):
        self.panel = None
        self.widget = None
        self.reset()

    def run_lines(self, code_lines):
        auto_indent = self.widget.auto_indent
        self.widget.auto_indent = False
        for line in code_lines:
            if line.rstrip():
                self.widget.write(line)
                self.widget._processLine()
                if self.widget.interrupt_in_last_line:
                    break
        self.widget.auto_indent = auto_indent

    def run_lines_hidden(self, code_lines):
        for line in code_lines:
            self.widget.IP.api.ex(line)

    def show(self):
        self.panel.show_all()

    def hide(self):
        self.panel.hide_all()

    def visible(self):
        return self.panel.props.visible

    def grab_focus(self, panel):
        self.widget.grab_focus()

    def reset(self):
        if self.panel is not None:
            self.panel.destroy()
            self.widget.destroy()
        self.panel = gtk.ScrolledWindow()
        self.panel.set_policy(gtk.POLICY_AUTOMATIC,
                              gtk.POLICY_AUTOMATIC)
        self.panel.set_size_request(750, 220)
        self.widget = SnakedIPythonView()
        self.widget.modify_font(pango.FontDescription(FONT))
        self.widget.set_wrap_mode(gtk.WRAP_CHAR)
        self.panel.add(self.widget)
        self.panel.show_all()

    def enable_matplotlib_support(self):
        try:
            import matplotlib
        except ImportError:
            pass
        else:
            self.run_lines_hidden(['import matplotlib',
                                  'matplotlib.use("GTKAgg")',
                                  'matplotlib.interactive(1)'])

    def get_last_run_command(self):
        return self.widget.last_run_command


def get_selection_or_current_line(editor):

    # these routines are borrowed from hash_comment plugin
    def make_line_traversor(buffer, r):
        start, end = r
        start, stop = start.get_line(), end.get_line() + 1

        def inner():
            for i in xrange(start, stop):
                yield buffer.get_iter_at_line(i)

        return inner

    def get_line_text(iter):
        if not iter.starts_line():
            iter = iter.copy()
            iter.set_line(iter.get_line())

        end = iter.copy()
        if not end.ends_line():
            end.forward_to_line_end()

        return iter.get_text(end)

    def get_bounds(editor):
        if editor.buffer.get_has_selection():
            start, end = editor.buffer.get_selection_bounds()
            if start.ends_line():
                start.set_line(start.get_line() + 1)

            if end.starts_line():
                end.set_line(end.get_line() - 1)

            return start, end
        else:
            cursor = editor.cursor
            return cursor, cursor.copy()

    r = get_bounds(editor)
    traversor = make_line_traversor(editor.buffer, r)
    return [get_line_text(l) for l in traversor()]


import platform
if platform.system() == 'Windows':
    FONT = 'Lucida Console 9'
else:
    FONT = 'Luxi Mono 10'

ipython_runner = []


def init(injector):
    injector.bind('editor', 'toggle-ipython', 'View/Toggle _IPython', show_ipython).to('<ctrl>i')
    injector.bind('editor', 'ipython-run-current-code',
        'Python/Run current code', send_code).to('<ctrl>r')
    injector.bind('editor', 'ipython-run-file', 'Python/Run file', run_file).to('F6')
    injector.bind('editor', 'ipython-run-last', 'Python/Run last command', run_last).to('<shift>F6')
    injector.bind('editor', 'ipython-debug', 'Python/Debug', debug_file).to('<ctrl>F6')
    injector.bind('editor', 'restart-ipython', 'Python/Restart IPython',
        restart_ipython).to('<ctrl><shift>i')

    from snaked.core.prefs import add_option

    add_option('IPYTHON_GRAB_FOCUS_ON_SHOW', True,
        'Option controls ipython panel focus grabbing on its show')
    add_option('IPYTHON_MATPLOTLIB_INTERACTIVE_SUPPORT', False,
        'Option controls matplotlib interactive mode in ipython console')
    add_option('IPYTHON_AUTOEXECUTE', '',
        'Automatically run the specified scripts when the console is started.')


def get_ipython_runner(editor):
    try:
        return ipython_runner[0]
    except IndexError:
        pass

    root = editor.project_root
    if root:
        os.chdir(root)

    ipython_runner.append(IPythonRunner())
    if editor.conf['IPYTHON_MATPLOTLIB_INTERACTIVE_SUPPORT']:
        ipython_runner[0].enable_matplotlib_support()
    if editor.conf['IPYTHON_AUTOEXECUTE']:
        ipython_runner[0].run_lines_hidden(editor.snaked_conf['IPYTHON_AUTOEXECUTE'].split('\n'))

    editor.window.append_panel(ipython_runner[0].panel)\
        .on_activate(ipython_runner[0].grab_focus)

    return ipython_runner[0]

def show_ipython(editor):
    runner = get_ipython_runner(editor)
    editor.window.popup_panel(runner.panel, editor.conf['IPYTHON_GRAB_FOCUS_ON_SHOW'])


def get_selection_or_buffer(editor):
    if editor.buffer.get_has_selection():
        return editor.buffer.get_text(*editor.buffer.get_selection_bounds())
    else:
        return editor.text


def send_code(editor):
    lines = get_selection_or_current_line(editor)
    show_and_run(editor, lines)


def show_and_run(editor, lines):
    runner = get_ipython_runner(editor)
    editor.window.popup_panel(runner.panel)
    runner.run_lines(lines)


def run_last(editor):
    runner = get_ipython_runner(editor)
    cmd = runner.get_last_run_command()
    if cmd is not None:
        show_and_run(editor, [cmd])
    else:
        editor.message('No recent run command.')


def run_file(editor):
    lines = ['%%run %s' % editor.uri]
    show_and_run(editor, lines)


def debug_file(editor):
    lines = ['%%run -d %s' % editor.uri]
    show_and_run(editor, lines)


def restart_ipython(editor):
    runner = get_ipython_runner(editor)

    root = editor.project_root
    if root:
        os.chdir(root)

    runner.reset()
    editor.window.append_panel(ipython_runner[0].panel)\
        .on_activate(runner.grab_focus)
    editor.window.popup_panel(runner.panel, True)
