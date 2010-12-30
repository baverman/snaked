# -*- coding: utf-8 -*-

# this file is a modified version of source code from the Accerciser project
# http://live.gnome.org/accerciser

"""
Backend to the console plugin.

@author: Eitan Isaacson
@organization: IBM Corporation
@copyright: Copyright (c) 2007 IBM Corporation
@license: BSD

All rights reserved. This program and the accompanying materials are made
available under the terms of the BSD which accompanies this distribution, and
is available at U{http://www.opensource.org/licenses/bsd-license.php}
"""

import gtk
import re
import sys
import os
import pango
import subprocess
from StringIO import StringIO

try:
    import IPython
except Exception, e:
    raise ImportError('Error importing IPython (%s)' % str(e))

ansi_colors = {
    '0;30': 'Black',
    '0;31': 'Red',
    '0;32': 'Green',
    '0;33': 'Brown',
    '0;34': 'Blue',
    '0;35': 'Purple',
    '0;36': 'Cyan',
    '0;37': 'LightGray',
    '1;30': 'DarkGray',
    '1;31': 'DarkRed',
    '1;32': 'SeaGreen',
    '1;33': 'Yellow',
    '1;34': 'LightBlue',
    '1;35': 'MediumPurple',
    '1;36': 'LightCyan',
    '1;37': 'White',
    }


class IterableIPShell:

    def __init__(
        self,
        argv=None,
        user_ns=None,
        user_global_ns=None,
        cin=None,
        cout=None,
        cerr=None,
        input_func=None,
        ):

        if input_func:
            IPython.iplib.raw_input_original = input_func
        if cin:
            IPython.Shell.Term.cin = cin
        if cout:
            IPython.Shell.Term.cout = cout
        if cerr:
            IPython.Shell.Term.cerr = cerr

        if argv is None:
            argv = []

        # This is to get rid of the blockage that occurs during
        # IPython.Shell.InteractiveShell.user_setup()
        IPython.iplib.raw_input = lambda x: None

        self.interrupt_in_last_line = False

        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        sys.stdout = IPython.Shell.Term.cout
        sys.stderr = IPython.Shell.Term.cerr
        try:
            self.term = IPython.genutils.IOTerm(cin=cin, cout=cout,
                    cerr=cerr)
            os.environ['TERM'] = 'dumb'
            excepthook = sys.excepthook

            self.IP = IPython.Shell.make_IPython(argv, user_ns=user_ns,
                    user_global_ns=user_global_ns, embedded=True,
                    shell_class=IPython.Shell.InteractiveShell)
            self.IP.system = lambda cmd: \
                self.shell(self.IP.var_expand(cmd),
                           header='IPython system call: ',
                           verbose=self.IP.rc.system_verbose)
            self.IP.api.system = self.IP.system
            sys.excepthook = excepthook
            self.iter_more = 0
            self.initHistoryIndex()
            self.complete_sep = re.compile('[\s\{\}\[\]\(\)]')
        finally:
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr

    def execute(self):
        self.history_level = 0
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        sys.stdout = IPython.Shell.Term.cout
        sys.stderr = IPython.Shell.Term.cerr

        try:
            lines = self.IP.raw_input(None, self.iter_more).split('\n')
            for line in lines:
                try:
                    if self.IP.autoindent:
                        self.IP.readline_startup_hook(None)
                except KeyboardInterrupt:
                    self.IP.write('KeyboardInterrupt\n')
                    self.IP.resetbuffer()

                    # keep cache in sync with the prompt counter:
                    self.IP.outputcache.prompt_count -= 1

                    if self.IP.autoindent:
                        self.IP.indent_current_nsp = 0
                    self.iter_more = 0
                    self.interrupt_in_last_line = True
                except:
                    self.IP.showtraceback()
                    self.interrupt_in_last_line = True
                else:
                    self.iter_more = self.IP.push(line)
                    if self.IP.SyntaxTB.last_syntax_error \
                        and self.IP.rc.autoedit_syntax:
                        self.IP.edit_syntax_error()
                        self.interrupt_in_last_line = True
                    if self.IP.SyntaxTB.last_syntax_error \
                        or self.iter_more is None:
                        self.interrupt_in_last_line = True
                    else:
                        self.interrupt_in_last_line = False

                    if self.iter_more:
                        self.prompt = \
                            str(self.IP.outputcache.prompt2).strip()
                        if self.IP.autoindent:
                            self.IP.readline_startup_hook(self.IP.pre_readline)
                    else:
                        self.prompt = \
                            str(self.IP.outputcache.prompt1).strip()
                        if self._getRawHistoryList() \
                            and self._getRawHistoryList()[-1]:
                            self.commandProcessed(self._getRawHistoryList()[-1])
                if self.interrupt_in_last_line:
                    break
        finally:
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr

    def commandProcessed(self, command):
        pass

    def historyBack(self):
        history = ''
        # the below while loop is used to suppress empty history lines
        while (history == '' or history == '\n') \
            and self._history_level > 0:
            if self._history_level >= 1:
                self._history_level -= 1
            history = self._getHistory()
        return history

    def historyForward(self):
        history = ''
        # the below while loop is used to suppress empty history lines
        while (history == '' or history == '\n') \
            and self._history_level <= self._getHistoryMaxIndex():
            if self._history_level < self._getHistoryMaxIndex():
                self._history_level += 1
                history = self._getHistory()
            else:
                if self._history_level == self._getHistoryMaxIndex():
                    history = self._getHistory()
                    self._history_level += 1
                else:
                    history = ''
        return history

    def initHistoryIndex(self):
        self._history_level = self._getHistoryMaxIndex() + 1

    def _getRawHistoryList(self):
        return self.IP.input_hist_raw

    def _getHistoryMaxIndex(self):
        return len(self._getRawHistoryList()) - 1

    def _getHistory(self):
        rv = self.IP.input_hist_raw[self._history_level].strip('\n')
        return rv

    def updateNamespace(self, ns_dict):
        self.IP.user_ns.update(ns_dict)

    def complete(self, line):
        split_line = self.complete_sep.split(line)
        possibilities = self.IP.complete(split_line[-1])
        if possibilities:
            common_prefix = reduce(self._commonPrefix, possibilities)
            completed = line[:-len(split_line[-1])] + common_prefix
        else:
            completed = line
        return completed, possibilities

    def _commonPrefix(self, str1, str2):
        for i in range(len(str1)):
            if not str2.startswith(str1[:i + 1]):
                return str1[:i]
        return str1

    def shell(
        self,
        cmd,
        verbose=0,
        debug=0,
        header='',
        ):

        # stat = 0
        if verbose or debug:
            print header + cmd

        # flush stdout so we don't mangle python's buffering
        if not debug:
            # input, output = os.popen4(cmd)
            p = subprocess.Popen(
                cmd,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                close_fds=True,
                )
            input, output = p.stdin, p.stdout
            print output.read()
            output.close()
            input.close()


class ConsoleView(gtk.TextView):

    def __init__(self):
        gtk.TextView.__init__(self)
        self.modify_font(pango.FontDescription('Mono'))
        self.modify_base(gtk.STATE_NORMAL,
                         gtk.gdk.color_parse(ansi_colors['0;30']))
        self.modify_text(gtk.STATE_NORMAL,
                         gtk.gdk.color_parse(ansi_colors['0;37']))
        self.set_cursor_visible(True)
        self.text_buffer = self.get_buffer()
        self.mark = self.text_buffer.create_mark('scroll_mark',
                self.text_buffer.get_end_iter(), False)
        for code in ansi_colors:
            self.text_buffer.create_tag(code,
                    foreground=ansi_colors[code], weight=700)
        self.text_buffer.create_tag('0')
        self.text_buffer.create_tag('notouch', editable=False)
        self.color_pat = re.compile('\x01?\x1b\[(.*?)m\x02?')
        self.line_start = self.text_buffer.create_mark('line_start',
                self.text_buffer.get_end_iter(), True)
        self.connect('key-press-event', self._onKeypress)
        self.last_cursor_pos = 0
        self.auto_indent = True

    def write(self, text, editable=False):
        segments = self.color_pat.split(text)
        segment = segments.pop(0)
        start_mark = self.text_buffer.create_mark(None,
                self.text_buffer.get_end_iter(), True)
        self.text_buffer.insert(self.text_buffer.get_end_iter(),
                                segment)

        if segments:
            ansi_tags = self.color_pat.findall(text)
            for tag in ansi_tags:
                i = segments.index(tag)
                if segments[i + 1]:
                    self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(),
                            segments[i + 1], tag)
                segments.pop(i)
                segments.pop(i)
        if not editable:
            self.text_buffer.apply_tag_by_name('notouch',
                    self.text_buffer.get_iter_at_mark(start_mark),
                    self.text_buffer.get_end_iter())
        self.text_buffer.delete_mark(start_mark)
        self.scroll_mark_onscreen(self.mark)

    def showPrompt(self, prompt):
        self.write(prompt)
        self.text_buffer.move_mark(self.line_start,
                                   self.text_buffer.get_end_iter())
        if self.auto_indent:
            self.write(' ' * self.IP.indent_current_nsp, editable=True)
        self.text_buffer.place_cursor(self.text_buffer.get_end_iter())

    def changeLine(self, text):
        iter = self.text_buffer.get_end_iter()
        self.text_buffer.delete(self.text_buffer.get_iter_at_mark(self.line_start),
                                iter)
        self.write(text, True)

    def getCurrentLine(self):
        rv = \
            self.text_buffer.get_slice(self.text_buffer.get_iter_at_mark(self.line_start),
                self.text_buffer.get_end_iter(), False)
        return rv

    def showReturned(self, text):
        iter = self.text_buffer.get_iter_at_mark(self.line_start)
        iter.forward_to_line_end()
        self.text_buffer.apply_tag_by_name('notouch',
                self.text_buffer.get_iter_at_mark(self.line_start),
                iter)
        self.write(text)
        if text:
            self.write('\n')
        self.showPrompt(self.prompt)

    def _onKeypress(self, obj, event):
        start_iter = self.text_buffer.get_iter_at_mark(self.line_start)
        if event.keyval == gtk.keysyms.Home:
            self.text_buffer.place_cursor(start_iter)
            return True
        if not event.string:
            return
        insert_mark = self.text_buffer.get_insert()
        insert_iter = self.text_buffer.get_iter_at_mark(insert_mark)
        selection_mark = self.text_buffer.get_selection_bound()
        selection_iter = \
            self.text_buffer.get_iter_at_mark(selection_mark)

        if start_iter.compare(insert_iter) <= 0 \
            and start_iter.compare(selection_iter) <= 0:
            return
        elif start_iter.compare(insert_iter) > 0 \
            and start_iter.compare(selection_iter) > 0:
            self.text_buffer.place_cursor(start_iter)
        elif insert_iter.compare(selection_iter) < 0:
            self.text_buffer.move_mark(insert_mark, start_iter)
        elif insert_iter.compare(selection_iter) > 0:
            self.text_buffer.move_mark(selection_mark, start_iter)

    def cursor_at_last_line(self):
        insert_iter = \
            self.text_buffer.get_iter_at_mark(self.text_buffer.get_insert())
        start_iter = self.text_buffer.get_iter_at_mark(self.line_start)
        return start_iter.compare(insert_iter) <= 0


class IPythonView(ConsoleView, IterableIPShell):

    def __init__(self):
        ConsoleView.__init__(self)
        self.cout = StringIO()
        IterableIPShell.__init__(self, cout=self.cout, cerr=self.cout,
                                 input_func=self.raw_input)
        self.interrupt = False
        self.connect('key_press_event', self.keyPress)
        self.execute()

        self.cout.truncate(0)
        self.showPrompt(self.prompt)

    def raw_input(self, prompt=''):
        if self.interrupt:
            self.interrupt = False
            raise KeyboardInterrupt
        return self.getCurrentLine()

    def keyPress(self, widget, event):
        if event.state & gtk.gdk.CONTROL_MASK and event.keyval == 99:
            self.interrupt = True
            self._processLine()
            return True
        elif event.keyval == gtk.keysyms.Return:
            self._processLine()
            return True
        elif not event.state & gtk.gdk.CONTROL_MASK \
            and self.cursor_at_last_line() and event.keyval \
            == gtk.keysyms.Up:
            self.changeLine(self.historyBack())
            return True
        elif not event.state & gtk.gdk.CONTROL_MASK \
            and self.cursor_at_last_line() and event.keyval \
            == gtk.keysyms.Down:
            self.changeLine(self.historyForward())
            return True
        elif event.keyval == gtk.keysyms.Tab:
            if not self.getCurrentLine().strip():
                return False
            completed, possibilities = \
                self.complete(self.getCurrentLine())
            if len(possibilities) > 1:
                slice = self.getCurrentLine()
                self.write('\n')
                for symbol in possibilities:
                    self.write(symbol + '\n')
                self.showPrompt(self.prompt)
            self.changeLine(completed or slice)
            return True

    def _processLine(self):
        self.write('\n')
        self.execute()
        rv = self.cout.getvalue()
        if rv:
            rv = rv.strip('\n')
        self.showReturned(rv)
        self.cout.truncate(0)
        self.initHistoryIndex()


