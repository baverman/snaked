import sys
import os.path

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT) 

from snaked.plugins.python.ropehints import ReHintDb
from rope.base.project import Project
from rope.base import libutils    

from rope.contrib.codeassist import code_assist

def get_rope_resource(project, uri):
    return libutils.path_to_resource(project, uri)

def func_with_unknown_type(lolwhat):
    lolwhat.s

class Lolwhat(object):
    def star(self):
        pass
        
    def superstar(self):
        pass

def test_func_param_hint():
    project = Project('/tmp')
    hintdb = ReHintDb(project)
    hintdb.add_hint('.*', 'lolwhat', 'test_ropehints.Lolwhat')
    module_path = os.path.join(os.path.dirname(__file__), __name__+'.py')
    source = open(module_path).read().decode('utf8')
    resource = get_rope_resource(project, module_path)

    proposals = code_assist(project, source, 419, resource=resource)
    assert ['superstar', 'star'] == [p.name for p in proposals]