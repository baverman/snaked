def func_with_unknown_type(lolwhat):
    lolwhat.s

def func_with_unknown_return(magick_arg):
    return magick_arg

def caller_of_func_with_unknown_return(lol):
    return func_with_unknown_return(lol).s

def caller_of_module_attribute():
    import re
    re.compile.s


import sys
import os.path

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT) 

from snaked.plugins.python.ropehints import ScopeHintProvider, ReScopeMatcher
from rope.base.project import Project
from rope.base import libutils    

from rope.contrib.codeassist import code_assist

def get_rope_resource(project, uri):
    return libutils.path_to_resource(project, uri)


class Lolwhat(object):
    def star(self):
        pass
        
    def superstar(self):
        pass

def get_project():
    path = os.path.join(os.path.dirname(__file__), 'tmp') 
    if not os.path.exists(path):
        os.mkdir(path)
    else:
        ropefolder = os.path.join(path, '.ropeproject')
        if os.path.exists(ropefolder):
            import shutil
            shutil.rmtree(ropefolder)
        
    return Project(path)

def get_hint_db(project):
    db = ReScopeMatcher()
    project.pycore.hintdb = ScopeHintProvider(project, db)
    return db

def test_func_param_hint():
    project = get_project() 
    hintdb = get_hint_db(project)
    hintdb.add_param_hint('.*', 'lolwhat', 'test_ropehints.Lolwhat()')
    module_path = os.path.join(os.path.dirname(__file__), __name__+'.py')
    source = open(module_path).read().decode('utf8')
    resource = get_rope_resource(project, module_path)

    proposals = code_assist(project, source, 50, resource=resource)
    assert ['superstar', 'star'] == [p.name for p in proposals]
    
def test_func_return():
    project = get_project() 
    hintdb = get_hint_db(project)
    hintdb.add_param_hint('test_ropehints.func_with_unknown_return', 'return', 'test_ropehints.Lolwhat()')
    module_path = os.path.join(os.path.dirname(__file__), __name__+'.py')
    source = open(module_path).read().decode('utf8')
    resource = get_rope_resource(project, module_path)

    proposals = code_assist(project, source, 204, resource=resource)
    assert ['superstar', 'star'] == [p.name for p in proposals]
    
def test_module_attribute():
    project = get_project()
    hintdb = get_hint_db(project)
    hintdb.add_attribute_hint('re$', 'compile$', 'test_ropehints.Lolwhat()')
    module_path = os.path.join(os.path.dirname(__file__), __name__+'.py')
    source = open(module_path).read().decode('utf8')
    resource = get_rope_resource(project, module_path)

    proposals = code_assist(project, source, 270, resource=resource)
    assert ['superstar', 'star'] == [p.name for p in proposals]
    
#def test_class_base():
#    project = get_project()
#    hintdb = ReHintDb(project)
#    hintdb.add_hint('^werkzeug$', '^Request$', 'werkzeug.wrappers.Request')
#
#    mod = project.pycore.get_module('flask.wrappers')
#    print mod['RequestBase'].get_object().get_attributes()
    