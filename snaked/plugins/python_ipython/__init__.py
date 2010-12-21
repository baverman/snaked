'''
IPythonView plugin for snaked editor
Author: Gu Ye <cooyeah at gmail dot com>
'''

import gtk
from ipython_view import IPythonView
import pango
import sys


class SnakedIPythonView(IPythonView):
    def __init__(self):
        IPythonView.__init__(self)
        #self.IP.autoindent = True

    def run_code(self, code, prompt='(Running...)'):
        orig_cout=sys.stdout

        self.write(prompt)
        sys.stdout=self.cout
        self.IP.runlines(code)
        sys.stdout=orig_cout
        self.flush()

    def flush(self):
      rv = self.cout.getvalue()
      if rv: rv=rv.strip('\n')
      self.showReturned(rv)
      self.cout.truncate(0)

class IPythonRunner:
    def __init__(self):
        self.panel = None
        self.widget = None
        self.reset()

    def run_lines(self,code_lines):
        for line in code_lines:
            self.widget.write(line)
            self.widget._processLine()

    def show(self):
        #self.widget.show()
        self.panel.show_all()

    def hide(self):
        self.panel.hide_all()

    def visible(self):
        return self.panel.props.visible

    def reset(self):
        if self.panel is not None:
            self.panel.destroy()
            self.widget.destroy()
        self.panel=gtk.ScrolledWindow()
        self.panel.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)
        self.panel.set_size_request(750,220)
        self.widget=SnakedIPythonView()
        self.widget.modify_font(pango.FontDescription(FONT))
        self.widget.set_wrap_mode(gtk.WRAP_CHAR)
        self.panel.add(self.widget)


def get_selection_or_current_line(editor):
    #these routines are borrowed from hash_comment plugin
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
if platform.system()=="Windows":
        FONT = "Lucida Console 9"
else:
        FONT = "Luxi Mono 10"


ipython_runner = []

def init(manager):
    manager.add_shortcut('ipython', '<ctrl>i', 'IPython', 'Toggle IPython console', show_ipython)
    manager.add_shortcut('run-current-code', '<ctrl>r', 'IPython', 'Send current line or selection to IPython', send_code)
    manager.add_shortcut('run-code-file', 'F6', 'IPython', 'Run current file in IPython', run_file)
    manager.add_shortcut('restart-ipython', '<ctrl><shift>i','IPython', 'Restart IPython', restart_ipython)

def get_ipython_runner(editor):
    try:
        return ipython_runner[0]
    except IndexError:
        pass

    ipython_runner.append(IPythonRunner())
    editor.add_widget_to_stack(ipython_runner[0].panel)
    return ipython_runner[0]

def show_ipython(editor):
    runner = get_ipython_runner(editor)
    if runner.visible():
        runner.hide()
        editor.view.grab_focus()
    else:
        runner.show()
        editor.popup_widget(runner.panel)
        runner.widget.grab_focus()

def get_selection_or_buffer(editor):
    if editor.buffer.get_has_selection():
        return  editor.buffer.get_text(*editor.buffer.get_selection_bounds())
    else:
        return editor.text

def send_code(editor):
    runner = get_ipython_runner(editor)
    lines = get_selection_or_current_line(editor)
    runner.run_lines(lines)

def run_file(editor):
    runner = get_ipython_runner(editor)
    line = [ 'run %s' % editor.uri ]
    runner.run_lines(line)

def restart_ipython(editor):
    runner = get_ipython_runner(editor)
    runner.reset()
    editor.add_widget_to_stack(ipython_runner[0].panel)
    runner.show()
    editor.popup_widget(runner.panel)
    runner.widget.grab_focus()
