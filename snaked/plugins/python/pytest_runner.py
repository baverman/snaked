import weakref

import glib
import pango
import gtksourceview2

from snaked.util import BuilderAware, join_to_file_dir

import pytest_launcher

class TestRunner(BuilderAware):
    """glade-file: pytest_runner.glade"""

    def __init__(self):
        super(TestRunner, self).__init__(join_to_file_dir(__file__, 'pytest_runner.glade'))

        self.buffer = gtksourceview2.Buffer()
        self.view = gtksourceview2.View()
        self.view.set_buffer(self.buffer)
        self.buffer_place.add(self.view)
        self.view.show()

        self.editor = None
        self.timer_id = None
        self.test_proc = None
        self.collected_nodes = {}
        self.failed_nodes = {}
        self.tests_count = 0
        self.executed_tests = 0
        self.hbox1.hide()

    def collect(self, conn):
        while conn.poll():
            msg = conn.recv()
            handler_name = 'handle_' + msg[0].lower()
            try:
                func = getattr(self, handler_name)
            except AttributeError:
                print 'TestRunner: %s not founded' % handler_name
            else:
                func(*msg[1:])

        return self.test_proc.is_alive()

    def run(self, editor, matches='', files=[]):
        self.editor_ref = weakref.ref(editor)

        self.tests.clear()
        self.collected_nodes.clear()
        self.failed_nodes.clear()
        self.tests_count = 0
        self.executed_tests = 0
        self.progress.set_text('Running tests')
        proc, conn = pytest_launcher.run_test(editor.project_root, matches, files)
        self.test_proc = proc
        self.timer_id = glib.timeout_add(100, self.collect, conn)

    def show(self, editor):
        self.editor_ref = weakref.ref(editor)
        self.hbox1.show()

    def hide(self):
        self.hbox1.hide()

    def handle_collect_folder(self, node, is_item=False):
        parent, sep, child = node.rpartition('::')
        parent = self.collected_nodes[parent] if parent else None

        self.collected_nodes[node] = self.tests.append(parent, (child, pango.WEIGHT_NORMAL))

        if is_item:
            self.tests_count += 1
            self.progress_adj.set_upper(self.tests_count)

        if self.tests_count > 1:
            self.tests_view.expand_all()
            self.tests_view.columns_autosize()
            self.tests_view.set_size_request(self.tests_view.size_request()[0], -1)

            self.hbox1.show()

    def handle_collect_item(self, node):
        self.handle_collect_folder(node, True)

    def handle_item_call(self, node):
        self.executed_tests += 1
        self.progress_adj.set_value(self.executed_tests)
        self.progress.set_text('Running test %d/%d' % (self.executed_tests, self.tests_count))

        self.tests.set(self.collected_nodes[node], 1, pango.WEIGHT_BOLD)

        path = self.tests.get_path(self.collected_nodes[node])
        self.tests_view.scroll_to_cell(path)

    def handle_pass(self, node):
        iter = self.collected_nodes[node]
        testname = self.tests.get_value(iter, 0)
        self.tests.set(iter, 0, u'\u2714 '.encode('utf8') + testname, 1, pango.WEIGHT_NORMAL)

    def handle_fail(self, node, msg):
        self.failed_nodes[node] = msg
        iter = self.collected_nodes[node]
        testname = self.tests.get_value(iter, 0)
        self.tests.set(iter, 0, u'\u2716 '.encode('utf8') + testname, 1, pango.WEIGHT_BOLD)

    def handle_end(self):
        self.progress_adj.set_value(self.tests_count)
        self.progress.set_text('Done')