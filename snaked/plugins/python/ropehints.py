import os.path
import re

import rope.base.oi.soi
from rope.base.pyobjectsdef import PyModule

def update_type_for(project, source, resource):
    pass
    
def infer_parameter_objects_with_hints(func):
    def inner(pyfunction):
        params_types = func(pyfunction)
        param_names = pyfunction.get_param_names(False)
        for i, name in enumerate(param_names):
            ptype = pyfunction.pycore.hintdb.get_function_param_type(pyfunction, name)
            if ptype != None:
                params_types[i] = ptype
        
        return params_types
        
    return inner

rope.base.oi.soi.infer_parameter_objects = infer_parameter_objects_with_hints(
    rope.base.oi.soi.infer_parameter_objects)


def infer_returned_object_with_hints(func):
    def inner(pyfunction, args):
        rtype = pyfunction.pycore.hintdb.get_function_param_type(pyfunction, 'return')
        if rtype is None:
            rtype = func(pyfunction, args)
        
        return rtype
        
    return inner

rope.base.oi.soi.infer_returned_object = infer_returned_object_with_hints(
    rope.base.oi.soi.infer_returned_object)


class HintDb(object):
    def __init__(self, project):
        self.type_cache = {}
        project.pycore.hintdb = self
        
    def get_function_param_type(self, pyfunc, name):
        scope_path = self.get_scope_path(pyfunc.get_scope())
        type_name = self.find_type_for(scope_path, name)
        if type_name:
            return self.get_type(pyfunc.pycore, type_name)
        else:
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
                
        module, sep, name = type_name.rpartition('.')
        if module:
            module = pycore.get_module(module)
            obj = module[name].get_object()
        else:
            obj = pycore.get_module(name)
        
        self.type_cache[type_name] = obj
        return obj

        
class ReHintDb(HintDb):
    def __init__(self, project):
        super(ReHintDb, self).__init__(project)
        self.db = []
        
    def add_hint(self, scope, name, object_type):
        self.db.append((re.compile(scope), re.compile(name), object_type))  

    def find_type_for(self, scope_path, name):
        for scope, vname, otype in self.db:
            if scope.search(scope_path) and vname.search(name):
                return otype
                
        return None
        
class FileHintDb(ReHintDb):
    def __init__(self, project):
        super(FileHintDb, self).__init__(project)
        self.hints_filename = os.path.join(project.ropefolder.real_path, 'hints')
        self.hints_loaded = False
        
    def refresh(self):
        self.hints_loaded = False
        
    def load_hints(self):
        if self.hints_loaded:
            return
        
        self.hints_loaded = True
        
        try:
            with open(self.hints_filename) as f:
                for l in f:
                    try:
                        scope, name, type = l.strip().split()
                        self.add_hint(scope, name, type)
                    except ValueError:
                        continue        
        except IOError:
            pass
        
    def find_type_for(self, *args):
        self.load_hints()
        return super(FileHintDb, self).find_type_for(*args)
