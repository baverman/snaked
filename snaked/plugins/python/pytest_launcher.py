import os
import multiprocessing
import time

def test_runner(conn, cwd, match, files):
    import pytest, sys
    os.chdir(cwd)
    sys.path.insert(0, cwd)

    args = ' '.join(['-q', ('-k %s' % match) if match else ''] + files)
    pytest.main(args, plugins=[Collector(conn)])

def run_test(project_dir, match=None, files=[]):
    conn, inconn = multiprocessing.Pipe()
    proc = multiprocessing.Process(target=test_runner, args=(inconn, project_dir, match, files))
    proc.start()

    return proc, conn


class Collector(object):
    def __init__(self, conn):
        self.conn = conn
        self._durations = {}
        self.tests = []

    def extract_trace(self, excinfo):
        """:type excinfo: py._code.code.ReprExceptionInfo"""

        result = []
        for entry in excinfo.reprtraceback.reprentries:
            result.append((entry.reprfileloc.path, entry.reprfileloc.lineno))

        return result

    def pytest_runtest_logreport(self, report):
        """:type report: _pytest.runner.TestReport()"""

        if report.passed:
            self.conn.send(('PASS', report.nodeid))
        elif report.failed:
            if report.when != "call":
                self.conn.send(('ERROR', report.nodeid, str(report.longrepr)))
            else:
                self.conn.send(('FAIL', report.nodeid, str(report.longrepr),
                    self.extract_trace(report.longrepr)))
        elif report.skipped:
            self.conn.send(('SKIP', report.nodeid))

    def pytest_runtest_call(self, item, __multicall__):
        names = tuple(item.listnames())
        self.conn.send(('ITEM_CALL', item.nodeid))
        start = time.time()
        try:
            return __multicall__.execute()
        finally:
            self._durations[names] = time.time() - start

    def get_parents(self, node):
        while True:
            parent = node.parent
            if parent:
                yield parent.name
                node = parent
            else:
                break

    def pytest_collectreport(self, report):
        """:type report: _pytest.runner.CollectReport()"""
        if report.failed:
            self.conn.send(('FAILED_COLLECT', report.nodeid, str(report.longrepr),
                self.extract_trace(report.longrepr)))

    def pytest_internalerror(self, excrepr):
        self.conn.send(('INTERNAL_ERROR', excrepr))

    def pytest_sessionstart(self, session):
        self.suite_start_time = time.time()
        self.conn.send(('START', str(session.fspath)))

    def pytest_sessionfinish(self, session, exitstatus, __multicall__):
        self.conn.send(('END', ))

    def pytest_collection_finish(self):
        self.conn.send(('COLLECTED_TESTS', self.tests))

    def pytest_deselected(self, items):
        for node in items:
            self.tests.remove(node.nodeid)

    def pytest_itemcollected(self, item):
        self.tests.append(item.nodeid)

    #def __getattr__(self, name):
    #    print 'getattr', name
    #    raise AttributeError()