from ropetest import testutils
from rope.contrib.codeassist import code_assist

from snaked.plugins.python.djangohints import DjangoHintProvider

def get_proposals(project, source, offset=None, **kwargs):
    head = 'from tests.djangotest.models import *\n'
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
    project.pycore.hintdb = DjangoHintProvider(project, 'tests.test_djangohints')
    request.addfinalizer(lambda: testutils.remove_project(project))
    return project

def test_common_field_names_must_be_in_proposals_for_model_instance(project):
    result = pset(get_proposals(project, 'Blog().'))
    assert 'name' in result
    assert 'id' in result
    assert 'bposts' in result

    result = pset(get_proposals(project, 'Post().'))
    assert 'body' in result
    assert 'blog' in result
    assert 'blog_id' in result

def test_proposals_for_objects_finder(project):
    assert 'objects' in pset(get_proposals(project, 'Blog.'))

    result = pset(get_proposals(project, 'Blog.objects.'))
    assert 'all' in result
    assert 'get' in result
    assert 'filter' in result

def test_manager_get_return_type_must_resolve_to_appropriate_model(project):
    result = pset(get_proposals(project, 'Blog.objects.get().'))
    assert 'name' in result
    assert 'id' in result
    assert 'bposts' in result

def test_manager_finder_methods_return_type_must_resolve_to_manager_itself(project):
    result = pset(get_proposals(project, 'Blog.objects.filter().'))
    assert 'filter' in result

    result = pset(get_proposals(project, 'Blog.objects.exclude().'))
    assert 'filter' in result

    result = pset(get_proposals(project, 'Blog.objects.select_related().'))
    assert 'filter' in result

def test_query_set_item_getting_and_iterating_must_resolve_to_model_type(project):
    result = pset(get_proposals(project, 'Blog.objects.all()[0].'))
    assert 'name' in result
    assert 'id' in result
    assert 'bposts' in result

    result = pset(get_proposals(project, 'Blog.objects.filter()[0].'))
    assert 'name' in result
    assert 'id' in result
    assert 'bposts' in result

    result = pset(get_proposals(project, 'for r in Blog.objects.filter():\n    r.'))
    assert 'name' in result
    assert 'id' in result
    assert 'bposts' in result

def test_foreign_fields_must_be_resolved_to_model_type(project):
    result = pset(get_proposals(project, 'Post().blog.'))
    assert 'name' in result
    assert 'id' in result
    assert 'bposts' in result

def test_foreign_set_must_be_resolved_to_model_manager(project):
    result = pset(get_proposals(project, 'Blog().bposts.all()[0].'))
    assert 'body' in result
    assert 'blog' in result
    assert 'blog_id' in result

    result = pset(get_proposals(project, 'for r in Blog().bposts.filter():\n    r.'))
    assert 'body' in result
    assert 'blog' in result
    assert 'blog_id' in result

    result = pset(get_proposals(project,
        'for blog in Blog.objects.filter(name="blog"):\n'
        '   for post in blog.bposts.all():\n'
        '       post.'))
    assert 'body' in result
    assert 'blog' in result
    assert 'blog_id' in result
