import os.path
import sys

import rope.base.pyobjects
import rope.base.pynames
import rope.base.builtins

from rope.base import exceptions

from .ropehints import HintProvider, get_attribute_scope_path

def add_django_support(composite_provider, settings='settings'):
    return composite_provider.add_hint_provider(
        DjangoHintProvider(composite_provider.project, settings))

def get_path_and_package(module_path, project_root):
    packages = [os.path.basename(module_path).rpartition('.')[0]]
    while True:
        path = os.path.dirname(module_path)
        if path == module_path:
            break

        module_path = path

        if module_path == project_root:
            break

        if os.path.exists(os.path.join(module_path, '__init__.py')):
            packages.append(os.path.basename(module_path))
        else:
            break

    return module_path, '.'.join(reversed(packages))

loaded_django_modules = {}
def load_django_module(pymodule, project_root):
    path = os.path.realpath(pymodule.resource.real_path)
    try:
        return loaded_django_modules[path]
    except KeyError:
        pass

    syspath, module = get_path_and_package(path, project_root)
    if syspath not in sys.path:
        sys.path.append(syspath)

    __import__(module)

    loaded_django_modules[path] = sys.modules[module]
    return sys.modules[module]


class DjangoHintProvider(HintProvider):
    def __init__(self, project, settings):
        super(DjangoHintProvider, self).__init__(project)

        self.settings = settings

    def get_attributes(self, scope_path, pyclass, attrs):
        """:type pyclass: rope.base.pyobjectsdef.PyClass"""

        if not hasattr(pyclass, 'get_superclasses'):
            return {}

        if not any('django.db.models.base.Model' in get_attribute_scope_path(c)
                for c in pyclass.get_superclasses()):
            return {}

        os.environ['DJANGO_SETTINGS_MODULE'] = self.settings

        module = load_django_module(pyclass.get_module(), self.project.address)
        model = getattr(module, pyclass.get_name())()

        attrs = {}
        for name in model._meta.get_all_field_names():
            f = model._meta.get_field_by_name(name)[0]

            if f.__class__.__name__ == 'ForeignKey':
                related_model_name = f.rel.to.__module__ + '.' + f.rel.to.__name__
                attrs[name] = rope.base.pynames.DefinedName(
                    rope.base.pyobjects.PyObject(self.get_type(related_model_name).get_object()))
                attrs[f.attname] = rope.base.pynames.DefinedName(rope.base.pyobjects.PyObject(None))
            elif f.__class__.__name__ == 'RelatedObject':
                related_model_name = f.model.__module__ + '.' + f.model.__name__
                attrs[name] = DjangoObjectsName(self.get_type(related_model_name).get_object(),
                    self.get_type('django.db.models.manager.Manager'))
            else:
                attrs[name] = rope.base.pynames.DefinedName(rope.base.pyobjects.PyObject(None))

        attrs['objects'] = DjangoObjectsName(pyclass,
            self.get_type('django.db.models.manager.Manager'))

        return attrs


class DjangoObjectsName(rope.base.pynames.PyName):
    def __init__(self, pyclass, name):
        self._orig_name = name
        self.model_type = pyclass

    def get_object(self):
        return DjangoObjectsObject(self.model_type, self._orig_name.get_object())


def proxy(obj):
    cls = obj.__class__
    class Cls(cls):
        def __init__(self, obj):
            self._orig = obj

        def __getattribute__(self, name):
            obj = cls.__getattribute__(self, '_orig')
            print 'getattr', obj, name
            return cls.__getattribute__(obj, name)

    return Cls(obj)

class GetHolder:
    def __init__(self, result):
        self.result = result

    def get(self, *args):
        return self.result

class DjangoObjectsObject(object):
    def __init__(self, pyclass, obj):
        self.model_type = pyclass
        self._orig_object = obj
        self.type = obj.type

    def get_attributes(self):
        attrs = self._orig_object.get_attributes()

        attrs['get'].pyobject.returned = GetHolder(self.model_type)
        attrs['filter'].pyobject.returned = GetHolder(self)
        attrs['exclude'].pyobject.returned = GetHolder(self)
        attrs['extra'].pyobject.returned = GetHolder(self)
        attrs['order_by'].pyobject.returned = GetHolder(self)
        attrs['select_related'].pyobject.returned = GetHolder(self)
        attrs['all'].pyobject.returned = GetHolder(self)

        attrs['__getitem__'] = rope.base.pynames.DefinedName(
            SimpleFunction(self.model_type, ['index']))

        attrs['__iter__'] = rope.base.pynames.DefinedName(
            SimpleFunction(rope.base.builtins.get_iterator(self.model_type)))

        return attrs

    def __getattr__(self, name):
        return getattr(self._orig_object, name)

    def get_attribute(self, name):
        try:
            return self.get_attributes()[name]
        except KeyError:
            raise exceptions.AttributeNotFoundError('Attribute %s not found' % name)

    def __getitem__(self, key):
        return self.get_attribute(key)

    def __contains__(self, key):
        return key in self.get_attributes()


class SimpleFunction(rope.base.pyobjects.AbstractFunction):

    def __init__(self, returned=None, argnames=[]):
        rope.base.pyobjects.AbstractFunction.__init__(self)
        self.argnames = argnames
        self.returned = returned

    def get_returned_object(self, args):
        return self.returned

    def get_param_names(self, special_args=True):
        return self.argnames