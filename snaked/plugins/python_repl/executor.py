import sys
import gc

import ast
import types

def execute(code, globals=None, locals=None):
    root = ast.parse(code, '<repl>', 'exec')
    for n, type in break_ast_to_exec_parts(root):
        eval(compile(n, '<repl>', type), globals, locals)

def break_ast_to_exec_parts(root):
    result = []
    for node in root.body:
        if isinstance(node, ast.Expr):
            n = ast.Interactive()
            n.body = [node]
            result.append((n, 'single'))
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
    print '    ' * level, obj.__code__.co_name, obj, obj.__module__
    if obj.__closure__:
        for f in obj.__closure__:
            f = f.cell_contents
            if isinstance(f, types.FunctionType):
                trace(f, level + 1)