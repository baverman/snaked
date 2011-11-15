import sys
import gc
import ast
import types
import code
import StringIO

from pickle import dumps


class Namespace(object):
    def __init__(self):
        self.data = {}

    def __getitem__(self, name):
        return self.data[name]

    def __setitem__(self, name, value):
        self.data[name] = value


class Interpreter(code.InteractiveInterpreter):
    def __init__(self):
        code.InteractiveInterpreter.__init__(self)
        self.buffer = StringIO.StringIO()

    def execute(self, source, lineno=None):
        oldstdout = sys.stdout
        oldstderr = sys.stderr
        sys.stdout = self.buffer
        sys.stderr = self.buffer
        try:
            tree = ast.parse(source, '<repl>', 'exec')
            if lineno:
                ast.increment_lineno(tree, lineno-1)

            for node, etype in break_ast_to_exec_parts(tree):
                result = eval(compile(node, '<repl>', etype), {}, self.locals)
                if etype == 'eval':
                    if result is not None:
                        self.write(repr(result) + '\n')
                    self.locals['___'] = self.locals.get('__', None)
                    self.locals['__'] = self.locals.get('_', None)
                    self.locals['_'] = result

        except SystemExit:
            raise
        except SyntaxError:
            self.showsyntaxerror()
        except:
            self.showtraceback()
        finally:
            sys.stdout = oldstdout
            sys.stderr = oldstderr

    def write(self, data):
        self.buffer.write(data)

    def get_buffer(self):
        data = self.buffer.getvalue()
        self.buffer = StringIO.StringIO()
        return data

def execute(code, globals=None, locals=None):
    root = ast.parse(code, '<repl>', 'exec')
    for n, type in break_ast_to_exec_parts(root):
        eval(compile(n, '<repl>', type), globals, locals)

def break_ast_to_exec_parts(root):
    result = []
    for node in root.body:
        if isinstance(node, ast.Expr):
            n = ast.Expression()
            n.body = node.value
            result.append((n, 'eval'))
        else:
            n = ast.Module()
            n.body = [node]
            result.append((n, 'exec'))

    return result

def patch(package_name, code):
    pkg = sys.modules[package_name]
    old_funcs = {}
    for name, obj in pkg.__dict__.iteritems():
        if isinstance(obj, types.FunctionType):
            old_funcs[name] = obj

    eval(compile(code, pkg.__file__, 'exec'), pkg.__dict__)

    for name, obj in pkg.__dict__.iteritems():
        if isinstance(obj, types.FunctionType):
            if name in old_funcs and obj is not old_funcs[name]:
                replace_code(name, old_funcs[name], obj)

def replace_code(name, old_func, new_func):
    old_closures = {}
    get_closures(old_func, name, old_closures)

    new_closures = {}
    get_closures(new_func, name, new_closures)

    old_consts = {}
    get_consts(old_func, name, old_consts)

    new_consts = {}
    get_consts(new_func, name, new_consts)

    for name in new_consts:
        if name in old_consts:
            for obj in gc.get_referrers(old_consts[name]):
                if isinstance(obj, types.FunctionType):
                    obj.__code__ = new_consts[name]

    old_func.__code__ = new_func.__code__

    for name in new_closures:
        if name in old_closures:
            old_closures[name].__code__ = new_closures[name].__code__

def get_closures(func, name, result):
    if func.__closure__:
        for f in func.__closure__:
            f = f.cell_contents
            if isinstance(f, types.FunctionType):
                fname = name + '.' + f.__name__
                result[fname] = f
                get_closures(f, fname, result)

def get_consts(func, name, result):
    for c in func.__code__.co_consts:
        if isinstance(c, types.CodeType):
            result[name + '.' + c.co_name] = c

def trace(obj, level):
    #print '    ' * level, obj.__code__.co_name, obj, obj.__module__
    if obj.__closure__:
        for f in obj.__closure__:
            f = f.cell_contents
            if isinstance(f, types.FunctionType):
                trace(f, level + 1)


def run_server(project_dir, executable=None, env=None):
    import os.path, time
    from subprocess import Popen
    from multiprocessing.connection import Client, arbitrary_address

    addr = arbitrary_address('AF_UNIX')

    executable = executable or sys.executable
    args = [executable, __file__, addr]

    environ = None
    if env:
        environ = os.environ.copy()
        environ.update(env)

    proc = Popen(args, cwd=project_dir, env=environ)
    start = time.time()
    while not os.path.exists(addr):
        if time.time() - start > 5:
            raise Exception('py.test launching timeout exceed')
        time.sleep(0.01)

    conn = Client(addr)

    return proc, conn


class Server(object):
    def __init__(self, conn):
        self.conn = conn
        self.interpreter = Interpreter()

    def run(self):
        conn = self.conn
        while True:
            if conn.poll(1):
                try:
                    args = conn.recv()
                except EOFError:
                    break
                except Exception:
                    import traceback
                    traceback.print_exc()
                    break

                if args[0] == 'close':
                    conn.close()
                    break
                else:
                    self.interpreter.execute(*args[1:])
                    result = self.interpreter.get_buffer()
                    try:
                        self.conn.send_bytes(dumps(result, 2))
                    except:
                        import traceback
                        traceback.print_exc()


if __name__ == '__main__':
    from multiprocessing.connection import Listener

    listener = Listener(sys.argv[1])
    conn = listener.accept()
    server = Server(conn)
    server.run()
