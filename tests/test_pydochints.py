from ropetest import testutils
from rope.contrib.codeassist import code_assist
from rope.base.project import NoProject

from snaked.util import join_to_file_dir

from snaked.plugins.python.dochints import DocStringHintProvider

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
    project.pycore.hintdb = DocStringHintProvider(project)
    request.addfinalizer(lambda: testutils.remove_project(project))
    return project


def test_func_param_hint(project):
    code = '''
def func(param):
    """:type param: Trololo"""
    param.'''

    result = pset(get_proposals(project, code))
    assert 'eduard' in result
    assert 'hill' in result

def test_func_return(project):
    code = '''
def func():
    """:rtype: Lolwhat"""

func().'''

    result = pset(get_proposals(project, code))
    assert 'superstar' in result
    assert 'star' in result
