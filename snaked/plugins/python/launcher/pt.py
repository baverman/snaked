import time
import sys

import pytest


class Collector(object):
    def __init__(self, send):
        self.send = send
        self._durations = {}
        self.tests = []

    def extract_trace(self, excinfo):
        """:type excinfo: py._code.code.ReprExceptionInfo"""

        result = []
        for entry in excinfo.reprtraceback.reprentries:
            result.append((entry.reprfileloc.path, entry.reprfileloc.lineno))

        return result

    def extract_output(self, report):
        result = str(report.longrepr)
        for s, d in report.sections:
            result += '\n\n===================== ' + s + '=======================\n' + d

        return result

    def pytest_runtest_logreport(self, report):
        """:type report: _pytest.runner.TestReport()"""

        if report.passed:
            self.send(('PASS', report.nodeid))
        elif report.failed:
            if report.when != "call":
                self.send(('ERROR', report.nodeid, self.extract_output(report),
                    self.extract_trace(report.longrepr)))
            else:
                self.send(('FAIL', report.nodeid, self.extract_output(report),
                    self.extract_trace(report.longrepr)))
        elif report.skipped:
            self.send(('SKIP', report.nodeid))

    def pytest_runtest_call(self, item, __multicall__):
        names = tuple(item.listnames())
        self.send(('ITEM_CALL', item.nodeid))
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
            self.send(('FAILED_COLLECT', report.nodeid, self.extract_output(report),
                self.extract_trace(report.longrepr)))

    def pytest_internalerror(self, excrepr):
        self.send(('INTERNAL_ERROR', excrepr))

    def pytest_sessionstart(self, session):
        self.suite_start_time = time.time()
        self.send(('START', str(session.fspath)))

    def pytest_sessionfinish(self, session, exitstatus, __multicall__):
        self.send(('END', ))

    def pytest_collection_finish(self):
        self.send(('COLLECTED_TESTS', self.tests))

    def pytest_deselected(self, items):
        for node in items:
            self.tests.remove(node.nodeid)

    def pytest_itemcollected(self, item):
        self.tests.append(item.nodeid)

    #def __getattr__(self, name):
    #    print 'getattr', name
    #    raise AttributeError()


if __name__ == '__main__':
    from multiprocessing.connection import Listener
    listener = Listener(sys.argv[1])
    conn = listener.accept()

    if sys.version_info[0] == 3:
        from pickle import dumps
        def sender(data):
            return conn.send_bytes(dumps(data, 2))
    else:
        sender = conn.send

    pytest.main(sys.argv[2:], plugins=[Collector(sender)])