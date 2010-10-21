import os.path
import re

import weakref

import rope.base.oi.soi
import rope.base.pyobjects
import rope.base.pynames
from rope.base import exceptions
from rope.base.pyobjectsdef import PyModule, PyPackage

class ReplacedName(rope.base.pynames.PyName):
    def __init__(self, pyobject, pyname):
        self.pyobject = pyobject
        self.pyname = pyname

    def get_object(self):
        return self.pyobject

    def get_definition_location(self):
        return self.pyname.get_definition_location()


def infer_parameter_objects_with_hints(func):
    def inner(pyfunction):
        params_types = func(pyfunction)
        
        try:
            hintdb = pyfunction.pycore.hintdb
        except AttributeError:
            return params_types
        
        param_names = pyfunction.get_param_names(False)
        for i, name in enumerate(param_names):
            ptype = hintdb.get_function_param_type(pyfunction, name)
            if ptype != None:
                params_types[i] = ptype
        
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
        
        rtype = hintdb.get_function_param_type(pyfunction, 'return')
        if rtype is None:
            rtype = func(pyfunction, args)
        
        return rtype
        
    return inner

rope.base.oi.soi.infer_returned_object = infer_returned_object_with_hints(
    rope.base.oi.soi.infer_returned_object)


def get_module_attribute_with_hints(func, what):
    def inner(self, name):
        #print what, self.pycore.modname(self.resource), name

        try:
            hintdb = self.pycore.hintdb
        except AttributeError:
            return func(self, name)

        try:
            original_pyname = func(self, name)
        except exceptions.AttributeNotFoundError:
            original_pyname = None
        
        result = hintdb.get_module_attribute(self, name, original_pyname)
        if not result:
            raise exceptions.AttributeNotFoundError()
        else:
            return result
        
    return inner
        
PyModule.get_attribute = get_module_attribute_with_hints(PyModule.get_attribute, 'mod')
PyPackage.get_attribute = get_module_attribute_with_hints(PyPackage.get_attribute, 'pkg')

class HintDb(object):
    def __init__(self, project):
        self.type_cache = {}
        self.module_attrs_cache = weakref.WeakKeyDictionary()
        project.pycore.hintdb = self
        
    def get_function_param_type(self, pyfunc, name):
        scope_path = self.get_scope_path(pyfunc.get_scope())
        type_name = self.find_type_for(scope_path, name)
        if type_name:
            pyname = self.get_type(pyfunc.pycore, type_name)
            if pyname:
                return pyname.get_object()
        
        return None
        
    def get_scope_path(self, scope):
        result = []
        current_scope = scope
        while current_scope is not None:
            pyobj = current_scope.pyobject
            if isinstance(pyobj, PyModule):
                name = pyobj.pycore.modname(pyobj.resource)
            else:
                name = pyobj.get_name()
        
            result.insert(0, name)
            current_scope = current_scope.parent
        
        return '.'.join(result)
        
    def find_type_for(scope_path, name):
        return None
        
    def get_type(self, pycore, type_name):
        try:
            return self.type_cache[type_name]
        except KeyError:
            pass
        
        module, sep, name = type_name.strip('()').rpartition('.')
        if module:
            module = pycore.get_module(module)
            try:
                pyname = module[name]
            except exceptions.AttributeNotFoundError:
                pyname = None
        else:
            pyname = pycore.get_module(name)
        
        self.type_cache[type_name] = pyname
        return pyname
        
    def get_module_attribute(self, pymodule, name, original_pyname):
        try:
            return self.module_attrs_cache[pymodule][name]
        except KeyError:
            pass

        scope_path = pymodule.pycore.modname(pymodule.resource)
        type_name = self.find_type_for(scope_path, name)
        if type_name:
            type = self.get_type(pymodule.pycore, type_name)
        else:
            type = None
        
        if type:
            if type_name.endswith('()'):
                obj = rope.base.pyobjects.PyObject(type.get_object())
                pyname = ReplacedName(obj, type)
            else:
                pyname = type
        else:
            pyname = original_pyname
        
        self.module_attrs_cache.setdefault(pymodule, {})[name] = pyname
        return pyname

        
class ReHintDb(HintDb):
    def __init__(self, project):
        super(ReHintDb, self).__init__(project)
        self.db = []
        
    def add_hint(self, scope, name, object_type):
        self.db.append((re.compile(scope), re.compile(name), object_type))  

    def find_type_for(self, scope_path, name):
        for scope, vname, otype in self.db:
            if scope.match(scope_path) and vname.match(name):
                #print 'matched', scope_path, name
                return otype
                
        return None
        
class FileHintDb(ReHintDb):
    def __init__(self, project):
        super(FileHintDb, self).__init__(project)
        self.hints_filename = os.path.join(project.ropefolder.real_path, 'hints')
        self.load_hints()
        
    def refresh(self):
        self.load_hints()
        
    def load_hints(self):
        self.db[:] = []
        self.module_attrs_cache.clear()
        self.type_cache.clear()
        
        if os.path.exists(self.hints_filename):
            with open(self.hints_filename) as f:
                for l in f:
                    try:
                        scope, name, type = l.strip().split()
                        self.add_hint(scope, name, type)
                    except ValueError:
                        continue