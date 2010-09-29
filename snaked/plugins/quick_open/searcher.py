import re

def get_pattern(what):
    parts = re.split(r'[./\\]', what)
    rexp = r'.*?[./\\].*?'.join(parts)
    p = re.compile(rexp)
    return p

def name_start_match(what):
    def inner(name, path):
        return name.startswith(what)

    return inner

def name_match(what):
    def inner(name, path):
        return what in name

    return inner
    
def path_match(what):
    def inner(name, path):
        return what in path
    
    return inner
        
def fuzzy_match(what):
    pattern = get_pattern(what)
    def inner(name, path):
        return pattern.search(path) is not None

    return inner
    
def dir_is_good(name, path):
    if name.startswith('.'):
        return False
    
    return True

def file_is_good(name, path):
    if name.endswith('.pyc') or name.endswith('.pyo'):
        return False
    
    return True

def search(root, top, match, already_matched):
    from os import listdir
    from os.path import join, isdir
    
    dirs_to_visit = []
    for name in listdir(join(root, top)):
        fullpath = join(root, top, name)
        path = join(top, name)
        
        if isdir(fullpath) and dir_is_good(name, path):
            dirs_to_visit.append(path)
        elif (name, top) not in already_matched and match(name, path) and file_is_good(name, path):
            yield name, top
            
    for path in dirs_to_visit:
        for p in search(root, path, match, already_matched):
            yield p
