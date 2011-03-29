import re, sys

import weakref

import rope.base.oi.soi
import rope.base.pyobjects
import rope.base.pynames
from rope.base import exceptions
from rope.base.pyobjectsdef import PyModule, PyPackage, PyClass
from rope.base.builtins import BuiltinModule

class ReplacedName(rope.base.pynames.PyName):
    def __init__(self, pyobject, pyname):
        self.pyobject = pyobject
        self.pyname = pyname

    def get_object(self):
        return self.pyobject

    def get_definition_location(self):
        return self.pyname.get_definition_location()


def builtin_module(self):
    try:
        __import__(self.name)
        return sys.modules[self.name]
    except ImportError:
        return
BuiltinModule.module = property(builtin_module)


def infer_parameter_objects_with_hints(func):
    def inner(pyfunction):
        params_types = func(pyfunction)

        try:
            hintdb = pyfunction.pycore.hintdb
        except AttributeError:
            return params_types

        scope_path = get_attribute_scope_path(pyfunction)
        provided_names = hintdb.get_function_params(scope_path, pyfunction)
        for i, t in enumerate(params_types):
            if i in provided_names:
                params_types[i] = provided_names[i]

        return params_types

    return inner

rope.base.oi.soi.infer_parameter_objects = infer_parameter_objects_with_hints(
    rope.base.oi.soi.infer_parameter_objects)


def infer_returned_object_with_hints(func):
    def inner(pyfunction, args):
        try:
            hintdb = pyfunction.pycore.hintdb
        except AttributeError:
            return func(pyfunction, args)

        scope_path = get_attribute_scope_path(pyfunction)
        params = hintdb.get_function_params(scope_path, pyfunction)
        try:
            return params['return']
        except KeyError:
            return func(pyfunction, args)

    return inner

rope.base.oi.soi.infer_returned_object = infer_returned_object_with_hints(
    rope.base.oi.soi.infer_returned_object)

def get_attribute_scope_path(obj, collected=''):
        if isinstance(obj, (PyModule, PyPackage)):
            if obj.resource:
                name = obj.pycore.modname(obj.resource)
            else:
                return collected
        else:
            name = obj.get_name()

        if collected:
            collected = name + '.' + collected
        else:
            collected = name

        try:
            scope = obj.get_scope().parent
        except AttributeError:
            return collected

        if scope:
            return get_attribute_scope_path(scope.pyobject, collected)
        else:
            return collected

def get_attributes_with_hints(func):
    def inner(self):
        result = func(self)

        if isinstance(self, PyModule) and self.resource and self.resource.name == '__init__.py':
            return result

        #print 'request attributes for', get_attribute_scope_path(self), self

        try:
            hintdb = self.pycore.hintdb
        except AttributeError:
            return result

        scope_path = get_attribute_scope_path(self)
        recursion_guard = '____' + scope_path

        if recursion_guard in self.__dict__:
            return result

        self.__dict__[recursion_guard] = True
        try:
            hinted_attrs = hintdb.get_attributes(scope_path, self, result)
            result.update(hinted_attrs)
        except:
            raise
        finally:
            del self.__dict__[recursion_guard]

        return result

    return inner

PyClass._get_structural_attributes = get_attributes_with_hints(PyClass._get_structural_attributes)
PyModule._get_structural_attributes = get_attributes_with_hints(PyModule._get_structural_attributes)
PyPackage._get_structural_attributes = get_attributes_with_hints(PyPackage._get_structural_attributes)


def get_superclasses_wrapper(func):
    def inner(self):
        bases = func(self)
        for i, base in enumerate(bases):
            if self is base and hasattr(self, 'replaces_name'):
                bases[i] = self.replaces_name.get_object()

        return bases

    return inner

PyClass.get_superclasses = get_superclasses_wrapper(PyClass.get_superclasses)


class HintProvider(object):
    def __init__(self, project):
        self._project = weakref.ref(project)

    @property
    def project(self):
        """Return rope project

        :rtype: rope.base.project.Project
        """
        return self._project()

    def get_function_params(self, scope_path, pyfunc):
        """Should resolve type for function's parameters `name`

        Also should resolve return type by setting 'return' item in result dict
        If there is no any type hints {} is returned
        """
        return {}

    def get_attributes(self, scope_path, pyobj, attrs):
        """Returns additional atributes for pymodule or pyclass"""
        return {}

    def get_type(self, type_name, scope=None):
        pycore = self.project.pycore
        module, sep, name = type_name.strip('()').rpartition('.')
        if module:
            module = pycore.get_module(module)
            try:
                pyname = module[name]
            except exceptions.AttributeNotFoundError:
                pyname = None
        elif scope:
            pyname = scope.lookup(name)
        else:
            pyname = pycore.get_module(name)

        return pyname


class ScopeHintProvider(HintProvider):
    """Working horse of type hinting

    Common usage is in conjunction with :class:`ReScopeMatcher` (also see examples there)
    """
    def __init__(self, project, scope_matcher):
        """:param project: rope project
        :param scope_matcher: one of :class:`ScopeMatcher` implementations.
        """
        super(ScopeHintProvider, self).__init__(project)
        self.matcher = scope_matcher

    def get_function_params(self, scope_path, pyfunc):
        result = {}
        for i, name in enumerate(pyfunc.get_param_names(False)+['return']):
            type_name = self.matcher.find_param_type_for(scope_path, name)
            if type_name:
                pyname = self.get_type(type_name)
                if pyname:
                    if name == 'return':
                        result['return'] = pyname.get_object()
                    else:
                        result[i] = pyname.get_object()

        return result

    def get_attributes(self, scope_path, pyclass, oldattrs):
        attrs = {}
        for name, type_name in self.matcher.find_attributes(scope_path):
            type = self.get_type(type_name)
            if type:
                if type_name.endswith('()'):
                    obj = rope.base.pyobjects.PyObject(type.get_object())
                    attrs[name] = ReplacedName(obj, type)
                else:
                    attrs[name] = type

                existing_attributes = pyclass.get_attributes()
                if name in existing_attributes:
                    type.get_object().replaces_name = existing_attributes[name]

        return attrs

class ScopeMatcher(object):
    """Abstract matcher class for :class:`ScopeHintProvider`"""

    def find_param_type_for(self, scope_path, name):
        """
        Return matched function param or return value type

        :param scope_path: function or method scope path (``module.Class.method`` or ``module.func``)
        :param name: function param name or `return` in case matching function return value type
        """

    def find_attributes(self, scope_path):
        """
        Return matched class attributes types

        :param scope_path: module.ClassName
        :return: iterator of (attribute, type) tuples
        """


class ReScopeMatcher(ScopeMatcher):
    """:class:`ScopeHintProvider` matcher based on regular expressions

    Matching is done with ``re.match`` function (pay attention to differences with ``re.search``)

    See :func:`add_attribute`, :func:`add_param_hint`.

    """
    def __init__(self):
        self.param_hints = []
        self.attributes = []

    def add_param_hint(self, scope, name, object_type):
        """Add function/method parameter or return value type hint.

        Very useful in case of mass type hinting. For example part of snaked's ``ropehints.py``::

            def init(provider):
                provider.db.add_param_hint('.*', 'editor$', 'snaked.core.editor.Editor()')
                provider.db.add_param_hint('snaked\.plugins\..*?\.init$', 'manager$',
                    'snaked.core.plugins.ShortcutsHolder()')

        Snaked consist of many small functions passing around current text buffer (named ``editor``)
        as parameter and first line allows to provide such type hint. Second line resolves all plugins
        ``init`` function's ``manager`` parameter.

        Or take look at Django's view function's request resolving::

                provider.db.add_param_hint('.*\.views\..*', 'request$', 'django.http.HttpRequest()')

        If name is ``return`` type hint is provided for function's return value type. Following
        example shows it::

            provider.db.add_param_hint('re\.compile$', 'return$', 're.RegexObject()')
            provider.db.add_param_hint('re\.search$', 'return$', 're.MatchObject()')
            provider.db.add_param_hint('re\.match$', 'return$', 're.MatchObject()')
            provider.db.add_attribute('re$', 'RegexObject', 'snaked.plugins.python.stub.RegexObject')
            provider.db.add_attribute('re$', 'MatchObject', 'snaked.plugins.python.stub.MatchObject')

        Take notice, ``re.compile``, ``re.search``, ``re.match`` return absent classes which are mapped
        with :func:`add_attribute_hint` to existing stubs later.
        """
        self.param_hints.append((re.compile(scope), re.compile(name), object_type))

    def add_attribute(self, scope, name, object_type):
        """Add attribute type hint for module or class/object

        Can be used to provide module attributes types, for example in case or complex
        module loading (werkzeug) or complex runtime behavior (flask). Here is example
        ``.ropeproject/ropehints.py``::

            def init(provider):
                provider.db.add_attribute('flask$', 'request', 'flask.wrappers.Request()')
                provider.db.add_attribute('werkzeug$', 'Request', 'werkzeug.wrappers.Request')

        What happens here? ``flask.request`` is magic proxy to isolate thread contexts from each other.
        In runtime it is ``flask.wrappers.Request`` object (in default flask setup), so first line
        adds this missing information. But this is not enough. ``flask.wrappers.Request`` is a child
        of ``werkzeug.Request`` which can not be resolved because of werkzeug's module
        loading system. So there is second line adding necessary mapping: module attribute
        ``werkzeug.Request`` should be ``werkzeug.wrappers.Request`` indeed. Take note about
        parentheses, ``flask.request`` is instance so type declared with them as opposite to
        ``werkzeug.Request`` which is class.

        Also one can add class attributes hint. Here is example from my django project::

            provider.db.add_attribute('django\.http\.HttpRequest$', 'cur', 'app.Cur')
            provider.db.add_attribute('django\.http\.HttpRequest$', 'render', 'app.render')

        Here are some explanations. Every ``request`` object has ``cur`` attribute
        (I know about contexts, don't ask me why I need it) which is instance of ``app.Cur``, so
        first line injects such info. Second line resolves ``render`` function also bounded to
        request.
        """
        self.attributes.append((re.compile(scope), name, object_type))

    def find_param_type_for(self, scope_path, name):
        for scope, vname, otype in self.param_hints:
            if scope.match(scope_path) and vname.match(name):
                return otype

        return None

    def find_attributes(self, scope_path):
        for scope, vname, otype in self.attributes:
            if scope.match(scope_path):
                yield vname, otype


class CompositeHintProvider(HintProvider):
    """Default snaked's hint provider

    It is created automatically for each rope project and passed to ``.ropeproject/ropehints.py``
    ``init`` function as first parameter.

    Contains build-in :class:`ScopeHintProvider` with it's scope matcher accessed via ``self.db``
    and :class:`DocStringHintProvider`.

    Also provides hints for ``re`` module. Custom providers can be
    added via :func:`add_hint_provider`::

        def init(provider):
            provider.db.add_class_attribute('django\.http\.HttpRequest$', 'render$', 'app.render')

            from snaked.plugins.python.djangohints import DjangoHintProvider
            provider.add_hint_provider(DjangoHintProvider(provider, 'settings'))

    """
    def __init__(self, project):
        super(CompositeHintProvider, self).__init__(project)

        self.attributes_cache = {}

        self.hint_provider = []

        self.db = ReScopeMatcher()
        self.db.add_param_hint('ropehints\.init$', 'provider$',
            'snaked.plugins.python.ropehints.CompositeHintProvider()')

        self.db.add_param_hint('re\.compile$', 'return$', 're.RegexObject()')
        self.db.add_param_hint('re\.search$', 'return$', 're.MatchObject()')
        self.db.add_param_hint('re\.match$', 'return$', 're.MatchObject()')
        self.db.add_attribute('re$', 'RegexObject', 'snaked.plugins.python.stub.RegexObject')
        self.db.add_attribute('re$', 'MatchObject', 'snaked.plugins.python.stub.MatchObject')

        self.add_hint_provider(ScopeHintProvider(project, self.db))

        # prepopulate popular dynamic modules
        existing_modules = project.prefs['extension_modules'] or []
        for m in ('os._path', 'itertools'):
            if m not in existing_modules:
                existing_modules.append(m)
        project.prefs['extension_modules'] = existing_modules
        project.prefs['ignore_bad_imports'] = True

        from .dochints import DocStringHintProvider
        self.add_hint_provider(DocStringHintProvider(project))

    def add_hint_provider(self, provider):
        """Inserts provider into collection.

        Last added provider has max priority.
        """

        self.hint_provider.insert(0, provider)
        return provider

    def get_function_params(self, scope_path, pyfunc):
        for p in self.hint_provider:
            result = p.get_function_params(scope_path, pyfunc)
            if result:
                return result

        return {}

    def get_attributes(self, scope_path, pyclass, attrs):
        try:
            return self.attributes_cache[scope_path]
        except KeyError:
            pass

        new_attrs = {}
        for p in self.hint_provider:
            new_attrs.update(p.get_attributes(scope_path, pyclass, attrs))

        self.attributes_cache[scope_path] = new_attrs
        return new_attrs