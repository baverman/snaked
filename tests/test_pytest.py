import sys
import time

from uxie.utils import join_to_file_dir
from snaked.plugins.python.pytest_launcher import run_test

def collect_results(proc, conn):
    result = []
    while True:
        while conn.poll():
            try:
                data = conn.recv()
                result.append(data)
            except EOFError:
                break

        if proc.poll() is not None:
            conn.close()
            break

        time.sleep(0.1)

    return result

def test_runner_must_return_collected_tests():
    result = collect_results(*run_test(join_to_file_dir(__file__), files=['python_test/first.py']))

    assert result[0][0] == ('START')
    assert result[1] == ('COLLECTED_TESTS', ['python_test/first.py::test_first',
        'python_test/first.py::test_second', 'python_test/first.py::test_third',
        'python_test/first.py::test_fourth'])

def test_runner_must_return_right_status_for_failed_collect():
    result = collect_results(*run_test(join_to_file_dir(__file__),
        files=['python_test/module_with_errors.py']))

    assert result[1][0] == 'FAILED_COLLECT'
    assert result[1][1] == 'python_test/module_with_errors.py'
    assert result[1][3] == [('python_test/module_with_errors.py', 4)]
    assert 'NameError' in result[1][2]

def test_runner_must_return_runned_test_results():
    result = collect_results(*run_test(join_to_file_dir(__file__), files=['python_test/first.py']))
    assert result[2] == ('ITEM_CALL', 'python_test/first.py::test_first')
    assert result[3] == ('PASS', 'python_test/first.py::test_first')

    assert result[6] == ('ITEM_CALL', 'python_test/first.py::test_third')
    assert result[7] == ('SKIP', 'python_test/first.py::test_third')

    assert result[5][:2] == ('FAIL', 'python_test/first.py::test_second')
    assert 'AssertionError' in result[5][2]

    assert result[9][:2] == ('FAIL', 'python_test/first.py::test_fourth')
    assert 'AttributeError' in result[9][2]

def test_runner_must_ignore_skipped_collected_items():
    result = collect_results(*run_test(join_to_file_dir(__file__), None,
        'test_first', files=['python_test/first.py']))

    assert result[1] == ('COLLECTED_TESTS', ['python_test/first.py::test_first'])

def test_runner_must_return_output_of_failed_tests():
    result = collect_results(*run_test(join_to_file_dir(__file__), files=['python_test/first.py'],
        match='test_second'))

    assert 'test-second-output' in result[3][2]