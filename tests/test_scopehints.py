from ropetest import testutils
from rope.contrib.codeassist import code_assist
from rope.base.project import NoProject

from snaked.util import join_to_file_dir

from snaked.plugins.python.ropehints import ScopeHintProvider, ReScopeMatcher

def get_proposals(project, source, offset=None, **kwargs):
    head = 'from tests.scopetest import *\n\n'
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
    matcher = ReScopeMatcher()
    project.pycore.hintdb = ScopeHintProvider(project, matcher)
    project.db = matcher
    request.addfinalizer(lambda: testutils.remove_project(project))
    return project

def test_func_param_hint(project):
    project.db.add_param_hint('tests\.module\.func$', 'lolwhat$', 'tests.scopetest.Lolwhat()')

    result = pset(get_proposals(project, 'def func(lolwhat):\n    lolwhat.'))
    assert 'superstar' in result
    assert 'star' in result

def test_func_return(project):
    project.db.add_param_hint('tests\.module\.func$', 'return$', 'tests.scopetest.Lolwhat()')
    result = pset(get_proposals(project, 'def func():\n    return None\n\nfunc().'))
    assert 'superstar' in result
    assert 'star' in result

def test_module_attribute(project):
    project.db.add_attribute('re$', 'compile', 'tests.scopetest.Lolwhat()')

    result = pset(get_proposals(project, 'import re\nre.compile.'))
    assert 'superstar' in result
    assert 'star' in result

def test_class_attributes(project):
    project.db.add_attribute('tests\.scopetest\.Lolwhat$', 'trololo', 'tests.scopetest.Trololo()')

    result = pset(get_proposals(project, 'Lolwhat().trololo.'))
    assert 'eduard' in result
    assert 'hill' in result

def test_getting_recursive_attribute(project):
    project.db.add_attribute('tests\.scopetest$', 'Trololo', 'tests.scopetest.ModifiedTrololo')

    result = pset(get_proposals(project, 'Trololo().'))
    assert 'anatolievich' in result

def test_getting_recursive_attribute_from_extension(project):
    project.prefs['extension_modules'] = ['gtk._gtk']

    project.db.add_attribute('gtk$', 'TextView', 'tests.scopetest.ModifiedTextView')

    result = pset(get_proposals(project, 'gtk.TextView().'))
    assert 'set_buffer' in result

    result = pset(get_proposals(project, 'gtk.TextView().get_buffer().'))
    assert 'get_iter_at_mark' in result