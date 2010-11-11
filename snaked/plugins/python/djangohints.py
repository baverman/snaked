import os, sys

import rope.base.pyobjects
import rope.base.pynames

from .ropehints import HintProvider, get_attribute_scope_path

os.environ['DJANGO_SETTINGS_MODULE'] = 'snaked.plugins.python.djangohints'

loaded_django_modules = {}
def load_django_module(pymodule):
    path = pymodule.resource.real_path
    try:
        return loaded_django_modules[path]
    except KeyError:
        pass
    
    class Stub: pass
    Stub.__name__ = 'snaked_stub_site.model'
    
    sys.modules[Stub.__name__] = Stub
    namespace = {'__name__':Stub.__name__}
    execfile(path, namespace)
    
    loaded_django_modules[path] = namespace
    return namespace
    

class DjangoHintProvider(HintProvider):

    def get_class_attributes(self, scope_path, pyclass, attrs):
        """:type pyclass: rope.base.pyobjectsdef.PyClass"""

        if not any('django.db.models.base.Model' in get_attribute_scope_path(c)
                for c in pyclass.get_superclasses()):
            return
        
        module = load_django_module(pyclass.get_module())
        model = module[pyclass.get_name()]()
        
        for name in model._meta.get_all_field_names():
            f = model._meta.get_field_by_name(name)[0]
            if name not in attrs:
                attrs[name] = rope.base.pynames.DefinedName(rope.base.pyobjects.PyObject(None))
            
            if f.__class__.__name__ == 'ForeignKey':
                attrs[f.attname] = rope.base.pynames.DefinedName(rope.base.pyobjects.PyObject(None))