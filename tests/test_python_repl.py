import sys
from inspect import cleandoc

from snaked.plugins.python_repl.executor import execute, patch, Interpreter

def remove_test_modules():
    try:
        del sys.modules['tests.patcher.first']
    except KeyError:
        pass

def test_simple_statement_execution(capsys):
    code = "x = 5\ny=10\nx + y\n"
    ctx = {}

    execute(code, ctx)

    assert ctx['x'] == 5
    assert ctx['y'] == 10

    out = capsys.readouterr()[0]
    assert out == '15\n'

    code = "'123'\n456"
    execute(code, ctx)
    out = capsys.readouterr()[0]
    assert out == "'123'\n456\n"

def test_trivial_funcs_runtime_code_replace():
    remove_test_modules()
    from tests.patcher.first import simple_func

    result = simple_func(1)
    assert result == 3

    code = '''
def simple_func(x):
    return x + CONST + 1
    '''

    patch('tests.patcher.first', code)

    result = simple_func(1)
    assert result == 4

def test_decorated_funcs_runtime_code_replace():
    remove_test_modules()
    from tests.patcher.first import decorated_func, another_decorated_func

    result = decorated_func(1)
    assert result == 2

    result = another_decorated_func(3)
    assert result == 16

    code = '''
@decorator
def decorated_func(x):
    return x + 1
    '''

    patch('tests.patcher.first', code)

    result = decorated_func(1)
    assert result == 3

    result = another_decorated_func(3)
    assert result == 16

def test_decorator_runtime_code_replace():
    remove_test_modules()
    from tests.patcher.first import decorated_func, another_decorated_func

    result = decorated_func(1)
    assert result == 2

    result = another_decorated_func(3)
    assert result == 16

    code = '''
def decorator(func):
    def inner(x):
        return func(x+3)

    return inner
    '''

    patch('tests.patcher.first', code)

    result = decorated_func(1)
    assert result == 4

    result = another_decorated_func(3)
    assert result == 36

def test_interpreter():
    e = Interpreter()
    e.execute('a = 10; a')
    e.execute('a + 10')
    result = e.get_buffer()
    assert result == '10\n20\n'

    e.execute('a + 20')
    result = e.get_buffer()
    assert result == '30\n'
