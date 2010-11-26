import time

from snaked.util import join_to_file_dir
from snaked.plugins.python.pytest_launcher import run_test

def collect_results(proc, conn):
    result = []
    while True:
        while conn.poll():
            result.append(conn.recv())

        if not proc.is_alive():
            break

        time.sleep(0.1)

    return result

def test_runner_must_return_collected_tests():
    result = collect_results(*run_test(join_to_file_dir(__file__), files=['python_test/first.py']))

    assert result[0] == ('COLLECT_FOLDER', 'python_test/first.py')
    assert result[1] == ('COLLECT_ITEM', 'python_test/first.py::test_first')
    assert result[2] == ('COLLECT_ITEM', 'python_test/first.py::test_second')
    assert result[3] == ('COLLECT_ITEM', 'python_test/first.py::test_third')
    assert result[4] == ('COLLECT_ITEM', 'python_test/first.py::test_fourth')

def test_runner_must_return_right_status_for_failed_collect():
    result = collect_results(*run_test(join_to_file_dir(__file__),
        files=['python_test/module_with_errors.py']))

    assert result[0] == ('COLLECT_FOLDER', 'python_test/module_with_errors.py')
    assert result[1][0] == 'FAILED_COLLECT'
    assert result[1][1] == 'python_test/module_with_errors.py'
    assert 'NameError' in result[1][2]

def test_runner_must_return_runned_test_results():
    result = collect_results(*run_test(join_to_file_dir(__file__), files=['python_test/first.py']))
    assert result[5] == ('ITEM_CALL', 'python_test/first.py::test_first')
    assert result[6] == ('PASS', 'python_test/first.py::test_first')

    assert result[9] == ('ITEM_CALL', 'python_test/first.py::test_third')
    assert result[10] == ('SKIP', 'python_test/first.py::test_third')

    assert result[8][:2] == ('FAIL', 'python_test/first.py::test_second')
    assert 'AssertionError' in result[8][2]

    assert result[12][:2] == ('FAIL', 'python_test/first.py::test_fourth')
    assert 'func_raise_exception' in result[12][2]