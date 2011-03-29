from ropetest import testutils
from rope.contrib.codeassist import code_assist
from rope.base.project import NoProject

from snaked.util import join_to_file_dir
from snaked.plugins.python.pygtkhints import add_gtk_extension_modules, PyGtkHintProvider

def get_proposals(project, source, offset=None, **kwargs):
    head = (
        'class Window(object):\n'
        '   """glade-file: sample.glade"""\n'
        '\n'
        '   def func(self):\n'
        '       '
    )

    source = head + source

    if offset is None:
        offset = len(source)
    else:
        offset += len(head)

    resource = NoProject().get_file(join_to_file_dir(__file__, 'pygtktest', 'module.py'))
    resource.read = lambda: ''

    return code_assist(project, source, offset, resource=resource, **kwargs)

def pset(proposals):
    return set(p.name for p in proposals)

def pytest_funcarg__project(request):
    project = testutils.sample_project()
    add_gtk_extension_modules(project)
    project.pycore.hintdb = PyGtkHintProvider(project)
    project.db = project.pycore.hintdb

    request.addfinalizer(lambda: testutils.remove_project(project))
    return project

def test_class_must_contain_objects_defined_in_glade_file(project):
    result = pset(get_proposals(project, 'self.'))
    assert 'window1' in result
    assert 'vbox1' in result

    result = pset(get_proposals(project, 'self.window1.'))
    assert 'set_title' in result

    result = pset(get_proposals(project, 'self.vbox1.'))
    assert 'pack_start' in result

def test_class_must_contain_objects_defined_in_glade_file_with_external_mapping(project):
    project.db.add_class('module.Window', join_to_file_dir(__file__, 'pygtktest', 'sample2.glade'))

    result = pset(get_proposals(project, 'self.'))
    assert 'window2' in result
    assert 'vbox2' in result

    result = pset(get_proposals(project, 'self.window2.'))
    assert 'set_title' in result

    result = pset(get_proposals(project, 'self.vbox2.'))
    assert 'pack_start' in result

def test_provider_must_resolve_params_of_handlers_defined_in_glade_file(project):
    result = pset(get_proposals(project, 'pass\n\n'
        '   def on_window1_delete_event(self, wnd):\n'
        '       wnd.'))
    assert 'set_title' in result

def test_provider_must_resolve_params_of_handlers_defined_in_glade_file_with_external_map(project):
    project.db.add_class('module.Window', join_to_file_dir(__file__, 'pygtktest', 'sample2.glade'))

    result = pset(get_proposals(project, 'pass\n\n'
        '   def on_window2_delete_event(self, wnd):\n'
        '       wnd.'))
    assert 'set_title' in result

def test_provider_must_allow_to_implement_glade_handlers(project):
    result = pset(get_proposals(project, 'pass\n\n'
        '   def on'))
    assert 'on_window1_delete_event' in result

def test_glib_proposals(project):
    module = project.pycore.get_module('glib')
    assert 'timeout_add' in module