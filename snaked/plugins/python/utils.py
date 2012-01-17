import sys
import os
from os.path import exists, join, expanduser, isdir, realpath

environments = {}

def which(binary_name):
    for p in os.environ.get('PATH', '').split(os.pathsep):
        path = join(p, binary_name)
        if exists(path):
            return path

    return None

def get_virtualenvwrapper_root():
    return realpath(os.getenv('WORKON_HOME', expanduser('~/.virtualenvs')))

def get_virtualenvwrapper_executables():
    root = get_virtualenvwrapper_root()
    result = {}
    if exists(root) and isdir(root):
        for p in os.listdir(root):
            epath = join(root, p, 'bin', 'python')
            if exists(epath):
                result[p] = epath

    return result

def get_virtualenvwrapper_executable(name):
    root = get_virtualenvwrapper_root()
    epath = join(root, name, 'bin', 'python')
    if exists(epath):
        return epath

def get_executable(conf):
    name = conf['PYTHON_EXECUTABLE']

    try:
        return conf['PYTHON_EXECUTABLES'][name]
    except KeyError:
        pass

    path = get_virtualenvwrapper_executable(name)
    if path:
        return path

    if name == 'default':
        return sys.executable
    elif name == 'python2':
        path = which('python2')
        if path:
            return path
    elif name == 'python3':
        path = which('python3')
        if path:
            return path

    return sys.executable

def get_env(conf):
    executable = get_executable(conf)

    try:
        env = environments[executable]
    except KeyError:
        import supplement.remote
        env = environments[executable] = supplement.remote.Environment(
            executable, conf['PYTHON_EXECUTABLE_ENV'])

    return env

def close_envs():
    for v in environments.values():
        v.close()
