import sys
import os
from os.path import exists, join

def which(binary_name):
    for p in os.environ.get('PATH', '').split(os.pathsep):
        path = join(p, binary_name)
        if exists(path):
            return path

    return None

def get_executable(conf):
    name = conf['PYTHON_EXECUTABLE']

    try:
        return conf['PYTHON_EXECUTABLES'][name]
    except KeyError:
        pass

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