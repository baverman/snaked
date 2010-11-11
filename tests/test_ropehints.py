def func_with_unknown_type(lolwhat):
    lolwhat.s

def func_with_unknown_return(magick_arg):
    return magick_arg

def caller_of_func_with_unknown_return(lol):
    return func_with_unknown_return(lol).s

def caller_of_module_attribute():
    import re
    re.compile.s

def caller_of_class_attribute():
    Lolwhat().trololo.e

def doc_string_return():
    """:rtype: Lolwhat"""

def caller_of_doc_string(param):
    """:type param: Trololo"""
    doc_string_return().s
    param.h


import sys
import os.path

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from snaked.plugins.python.ropehints import ScopeHintProvider, ReScopeMatcher
from snaked.plugins.python.dochints import DocStringHintProvider
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

class Trololo(object):
    def eduard(self):
        pass

    def hill(self):
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

def get_proposals(project, offset):
    module_path = os.path.join(os.path.dirname(__file__), __name__+'.py')
    source = open(module_path).read().decode('utf8')
    resource = get_rope_resource(project, module_path)

    return code_assist(project, source, offset, resource=resource)

def test_func_param_hint():
    project = get_project()
    hintdb = get_hint_db(project)
    hintdb.add_param_hint('.*', 'lolwhat', 'test_ropehints.Lolwhat()')

    proposals = get_proposals(project, 50)
    assert ['superstar', 'star'] == [p.name for p in proposals]

def test_func_return():
    project = get_project()
    hintdb = get_hint_db(project)
    hintdb.add_param_hint('test_ropehints.func_with_unknown_return', 'return', 'test_ropehints.Lolwhat()')

    proposals = get_proposals(project, 204)
    assert ['superstar', 'star'] == [p.name for p in proposals]

def test_module_attribute():
    project = get_project()
    hintdb = get_hint_db(project)
    hintdb.add_attribute_hint('re$', 'compile$', 'test_ropehints.Lolwhat()')

    proposals = get_proposals(project, 270)
    assert ['superstar', 'star'] == [p.name for p in proposals]

def test_class_attributes():
    project = get_project()
    hintdb = get_hint_db(project)

    hintdb.add_class_attribute('test_ropehints.Lolwhat$', 'trololo', 'test_ropehints.Trololo()')

    proposals = get_proposals(project, 328)
    assert ['eduard'] == [p.name for p in proposals]

def test_doc_string_hints():
    project = get_project()
    project.pycore.hintdb = DocStringHintProvider(project)

    proposals = get_proposals(project, 471)
    assert ['superstar', 'star'] == [p.name for p in proposals]

    proposals = get_proposals(project, 483)
    assert ['hill'] == [p.name for p in proposals]
