import re

patterns = {}

def get_pattern(what):
    try:
        return patterns[what]
    except KeyError:
        parts = re.split(r'[./\\]', what)
        rexp = r'.*?[./\\].*?'.join(parts)
        p = re.compile(rexp)
        patterns[what] = p
        return p

def match(path, what):
    if what in path:
        return True
    
    if get_pattern(what).search(path):
        return True
    
    return False

def dir_is_good(name, path):
    if name.startswith('.'):
        return False
    
    return True

def file_is_good(name, path):
    if name.endswith('.pyc') or name.endswith('.pyo'):
        return False
    
    return True

def search(root, top, what):
    from os import listdir
    from os.path import join, isdir
    
    dirs_to_visit = []
    for name in listdir(join(root, top)):
        fullpath = join(root, top, name)
        path = join(top, name)
        
        if isdir(fullpath) and dir_is_good(name, path):
            dirs_to_visit.append(path)
        elif match(path, what) and file_is_good(name, path):
            yield name, top
            
    for path in dirs_to_visit:
        for p in search(root, path, what):
            yield p
