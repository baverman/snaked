import sys
import os.path

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from ropetest import testutils
from rope.contrib.codeassist import code_assist
from rope.base.project import NoProject

from snaked.util import join_to_file_dir

from snaked.plugins.python.ropehints import ScopeHintProvider, ReScopeMatcher

def provide_scope_hints_for(project):
    matcher = ReScopeMatcher()
    project.pycore.hintdb = ScopeHintProvider(project, matcher)
    return matcher

def get_proposals(project, source, offset=None, **kwargs):
    head = 'from scopetest import *\n\n'
    source = head + source

    if offset is None:
        offset = len(source)
    else:
        offset += len(head)

    resource = NoProject().get_file(join_to_file_dir(__file__, 'module.py'))
    resource.read = lambda: ''

    return code_assist(project, source, offset, resource=resource, **kwargs)

def pset(proposals):
    return set(p.name for p in proposals)

def pytest_funcarg__project(request):
    project = testutils.sample_project()
    request.addfinalizer(lambda: testutils.remove_project(project))
    return project


def test_func_param_hint(project):
    hintdb = provide_scope_hints_for(project)
    hintdb.add_param_hint('module\.func$', 'lolwhat$', 'scopetest.Lolwhat()')

    result = pset(get_proposals(project, 'def func(lolwhat):\n    lolwhat.'))
    assert 'superstar' in result
    assert 'star' in result

def test_func_return(project):
    hintdb = provide_scope_hints_for(project)
    hintdb.add_param_hint('module\.func$', 'return$', 'scopetest.Lolwhat()')

    result = pset(get_proposals(project, 'def func():\n    return None\n\nfunc().'))
    assert 'superstar' in result
    assert 'star' in result

def test_module_attribute(project):
    hintdb = provide_scope_hints_for(project)
    hintdb.add_attribute('re$', 'compile', 'scopetest.Lolwhat()')

    result = pset(get_proposals(project, 'import re\nre.compile.'))
    assert 'superstar' in result
    assert 'star' in result

def test_class_attributes(project):
    hintdb = provide_scope_hints_for(project)
    hintdb.add_attribute('scopetest.Lolwhat$', 'trololo', 'scopetest.Trololo()')

    result = pset(get_proposals(project, 'Lolwhat().trololo.'))
    assert 'eduard' in result
    assert 'hill' in result
