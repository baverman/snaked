import os.path
import weakref

import glib
import pango
import gtk

from snaked.util import BuilderAware, join_to_file_dir

import pytest_launcher

class Escape(object): pass

class TestRunner(BuilderAware):
    """glade-file: pytest_runner.glade"""

    def __init__(self):
        super(TestRunner, self).__init__(join_to_file_dir(__file__, 'pytest_runner.glade'))

        self.buffer = gtk.TextBuffer()
        self.view = gtk.TextView()
        self.view.set_buffer(self.buffer)
        self.view.set_editable(False)
        self.view.set_wrap_mode(gtk.WRAP_WORD)
        self.buffer_place.add(self.view)
        self.view.show()

        self.editor_ref = None
        self.timer_id = None
        self.test_proc = None
        self.collected_nodes = {}
        self.failed_nodes = {}
        self.nodes_traces = {}
        self.nodes_buffer_positions = {}
        self.panel.hide()
        self.escape = None

    def collect(self, conn):
        while conn.poll():
            try:
                msg = conn.recv()
            except EOFError:
                break

            handler_name = 'handle_' + msg[0].lower()
            try:
                func = getattr(self, handler_name)
            except AttributeError:
                print 'TestRunner: %s not founded' % handler_name
            else:
                func(*msg[1:])

        return self.test_proc.poll() is None

    def run(self, editor, matches='', files=[]):
        self.editor_ref = weakref.ref(editor)
        self.stop_running_test()

        self.tests.clear()
        self.collected_nodes.clear()
        self.failed_nodes.clear()
        self.nodes_traces.clear()
        self.nodes_buffer_positions.clear()
        self.tests_count = 0
        self.executed_tests = 0
        self.passed_tests_count = 0
        self.failed_tests_count = 0
        self.skipped_tests_count = 0
        self.prevent_scroll = False
        self.buffer.delete(*self.buffer.get_bounds())
        self.buffer.node = None
        self.progress.set_text('Running tests')
        self.stop_run.show()
        self.trace_buttons.hide()

        proc, conn = pytest_launcher.run_test(editor.project_root, matches, files)
        self.test_proc = proc
        self.timer_id = glib.timeout_add(100, self.collect, conn)

    def show(self):
        self.editor_ref().popup_widget(self.panel)

    def hide(self, editor=None, *args):
        self.escape = None
        self.panel.hide()
        if editor:
            editor.view.grab_focus()

    def find_common_parent(self, nodes):
        if not nodes:
            return ''

        parent, _, _ = nodes[0].rpartition('::')
        while parent:
            if all(n.startswith(parent) for n in nodes):
                return parent

            parent, _, _ = parent.rpartition('::')

        return ''

    def handle_failed_collect(self, node, msg, trace):
        iter = self.collected_nodes[node] = self.tests.append(
            None, (node, pango.WEIGHT_NORMAL, node))

        self.add_trace(node, msg, trace)

        testname = self.tests.get_value(iter, 0)
        self.tests.set(iter, 0, u'\u2718 '.encode('utf8') + testname, 1, pango.WEIGHT_BOLD)

        self.show()
        self.resize_tests_view()
        self.tests_view.grab_focus()
        self.prevent_scroll = True

    def handle_collected_tests(self, nodes):
        common_parent = self.find_common_parent(nodes)

        self.tests_count = len(nodes)
        self.progress_adj.set_upper(self.tests_count)

        def append(node, node_name):
            parent, sep, child = node_name.rpartition('::')
            if parent:
                if parent not in self.collected_nodes:
                    append(parent, parent)

                self.collected_nodes[node] = self.tests.append(
                    self.collected_nodes[parent], (child, pango.WEIGHT_NORMAL, node))
            else:
                self.collected_nodes[node] = self.tests.append(
                    None, (child, pango.WEIGHT_NORMAL, node))

        for node in nodes:
            node_name = node
            if common_parent:
                node_name = node[len(common_parent)+2:]
            append(node, node_name)

        if self.tests_count > 1:
            self.show()
            self.resize_tests_view()

    def resize_tests_view(self):
        self.tests_view.expand_all()
        nw = self.tests_view.size_request()[0]
        w = self.tests_view_sw.get_size_request()[0]
        tw = self.panel.window.get_size()[0]
        if nw > w:
            if nw > tw/2: nw = tw/2
            self.tests_view_sw.set_size_request(nw, -1)

    def handle_item_call(self, node):
        self.executed_tests += 1
        self.progress_adj.set_value(self.executed_tests - 1)
        self.progress.set_text('Running test %d/%d' % (self.executed_tests, self.tests_count))

        self.tests.set(self.collected_nodes[node], 1, pango.WEIGHT_BOLD)

        if not self.prevent_scroll:
            path = self.tests.get_path(self.collected_nodes[node])
            self.tests_view.scroll_to_cell(path, None, True, 0.5)

    def handle_pass(self, node):
        self.passed_tests_count += 1
        iter = self.collected_nodes[node]
        testname = self.tests.get_value(iter, 0)
        self.tests.set(iter, 0, u'\u2714 '.encode('utf8') + testname, 1, pango.WEIGHT_NORMAL)

    def handle_skip(self, node):
        self.skipped_tests_count += 1
        iter = self.collected_nodes[node]
        testname = self.tests.get_value(iter, 0)
        self.tests.set(iter, 0, u'\u2731 '.encode('utf8') + testname, 1, pango.WEIGHT_NORMAL)

    def add_trace(self, node, msg, trace):
        self.failed_nodes[node] = msg

        result = []
        msg = msg.decode('utf-8')
        for filename, line in trace:
            search = u'%s:%d:' % (filename, line)
            idx = msg.find(search)
            result.append((filename, line, idx))

        self.nodes_traces[node] = result

    def handle_fail(self, node, msg, trace):
        self.failed_tests_count += 1
        self.prevent_scroll = True
        self.add_trace(node, msg, trace)
        iter = self.collected_nodes[node]
        testname = self.tests.get_value(iter, 0)
        self.tests.set(iter, 0, u'\u2718 '.encode('utf8') + testname, 1, pango.WEIGHT_BOLD)

        if self.failed_tests_count == 1:
            self.tests_view.set_cursor(self.tests.get_path(iter))
            self.show()
            self.resize_tests_view()
            self.tests_view.grab_focus()

    def handle_error(self, node, msg, err):
        self.handle_fail(node, msg, err)

    def handle_start(self, test_dir):
        self.test_dir = test_dir

    def handle_end(self):
        self.stop_run.hide()

        text = ['Done.']
        text.append('%d/%d passed.' % (self.passed_tests_count, self.tests_count))

        if self.skipped_tests_count:
            text.append('%d skipped.' % self.skipped_tests_count)

        if self.failed_tests_count:
            text.append('%d failed.' % self.failed_tests_count)

        self.progress.set_text(' '.join(text))
        self.progress_adj.set_value(self.tests_count)

        if not self.tests_count:
            self.editor_ref().message('There are no any tests to run')

        if self.tests_count == self.passed_tests_count == 1:
            self.editor_ref().message('Test PASSED')

    def on_tests_view_cursor_changed(self, view):
        path, column = view.get_cursor()
        iter = self.tests.get_iter(path)
        node = self.tests.get_value(iter, 2)

        buf = self.buffer

        if buf.node:
            self.nodes_buffer_positions[buf.node] = buf.get_iter_at_mark(
                buf.get_insert()).get_offset()

        self.trace_buttons.hide()

        if node in self.failed_nodes:
            buf.set_text(self.failed_nodes[node])
            buf.node = node
            if node in self.nodes_buffer_positions:
                buf.place_cursor(buf.get_iter_at_offset(self.nodes_buffer_positions[node]))
            else:
                buf.place_cursor(buf.get_bounds()[1])

            self.view.scroll_to_mark(buf.get_insert(), 0.001, use_align=True, xalign=1.0)
        else:
            self.buffer.set_text('')
            self.buffer.node = None

    def on_popup(self, widget, editor):
        self.escape = Escape()
        editor.push_escape(self.hide, self.escape)

    def on_tests_view_row_activated(self, view, path, *args):
        iter = self.tests.get_iter(path)
        node = self.tests.get_value(iter, 2)

        if node in self.nodes_traces:
            self.goto_trace(node, self.nodes_traces[node][0])
            if len(self.nodes_traces[node]) > 1:
                self.trace_buttons.show()

    def goto_trace(self, node, trace):
        filename, line, idx = trace

        if idx >= 0:
            self.buffer.place_cursor(self.buffer.get_iter_at_offset(idx))
            self.view.scroll_to_mark(self.buffer.get_insert(), 0.001, True, 1.0, 1.0)

        if not filename.startswith('/'):
            filename = os.path.join(self.test_dir, filename)

        e = self.editor_ref().open_file(filename, line - 1)
        e.view.grab_focus()

    def on_stop_run_activate(self, button):
        self.stop_running_test()

    def stop_running_test(self):
        if self.test_proc:
            if self.test_proc.poll() is None:
                glib.source_remove(self.timer_id)
                self.timer_id = None
                self.test_proc.terminate()
                self.test_proc.wait()

                self.stop_run.hide()
                self.progress.set_text('Stopped')

    def move_to_next_trace(self, is_back):
        if not self.buffer.node or not self.buffer.node in self.nodes_traces:
            return

        offset = self.buffer.get_iter_at_mark(self.buffer.get_insert()).get_offset()

        traces = self.nodes_traces[self.buffer.node]
        if is_back:
            traces = reversed(traces)

        for t in traces:
            if (is_back and t[2] < offset) or (not is_back and t[2] > offset):
                self.goto_trace(self.buffer.node, t)
                return

        self.editor_ref().message('There is no any traces to follow')

    def on_trace_up_activate(self, button):
        self.move_to_next_trace(True)

    def on_trace_down_activate(self, button):
        self.move_to_next_trace(False)