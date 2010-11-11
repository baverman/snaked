import sys
import os.path

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from ropetest import testutils
from rope.contrib.codeassist import code_assist

from snaked.plugins.python.djangohints import DjangoHintProvider

def provide_django_hints_for(project):
    project.pycore.hintdb = DjangoHintProvider(project)

def get_proposals(project, source, offset=None, **kwargs):
    head = 'from django_models_for_test import *\n'
    source = head + source

    if offset is None:
        offset = len(source)
    else:
        offset += len(head)

    return code_assist(project, source, offset, **kwargs)

def pset(proposals):
    return set(p.name for p in proposals)

def pytest_funcarg__project(request):
    project = testutils.sample_project()
    request.addfinalizer(lambda: testutils.remove_project(project))
    return project

def test_common_field_names_must_be_in_proposals_for_model_instance(project):
    provide_django_hints_for(project)

    result = pset(get_proposals(project, 'Blog().'))
    assert 'name' in result
    assert 'id' in result
    assert 'bposts' in result

    result = pset(get_proposals(project, 'Post().'))
    assert 'body' in result
    assert 'blog' in result
    assert 'blog_id' in result
