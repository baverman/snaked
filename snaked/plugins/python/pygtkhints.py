import os.path

import xml.sax.handler
import rope.base.pynames
from rope.base import libutils    

from .ropehints import HintProvider, get_attribute_scope_path

class ResourceAsModule(object):
    def __init__(self, resource):
        self.resource = resource
        
    def get_resource(self):
        return self.resource

    def get_module(self):
        return self
        

class GladeName(rope.base.pynames.PyName):
    def __init__(self, pyobject, module, line):
        self.pyobject = pyobject
        self.line = line
        self.module = module

    def get_object(self):
        return self.pyobject

    def get_definition_location(self):
        return self.module, self.line


class PyGtkHintProvider(HintProvider):
    def __init__(self, project):
        super(PyGtkHintProvider, self).__init__(project)
        self.gtk_aware_classes = {}
        self.cache = {} 
    
    def get_pygtk_class_name(self, gtk_class_name):
        return gtk_class_name.replace('Gtk', 'gtk.', 1) + '()'
    
    def get_class_attributes(self, pyclass):
        scope_path = get_attribute_scope_path(pyclass)
        try:
            return self.cache[scope_path]
        except KeyError:
            pass
        
        if scope_path not in self.gtk_aware_classes:
            attrs = {}
            self.cache[scope_path] = attrs
            return attrs
            
        glade_file = self.gtk_aware_classes[scope_path]
        resource = libutils.path_to_resource(self.project,
            os.path.join(self.project.address, glade_file))
        
        handler = GladeHandler()
        xml.sax.parseString(open(resource.real_path).read(), handler)
        
        attrs = {}
        for id, cls, line in handler.objects:
            type = self.get_type(self.get_pygtk_class_name(cls))
            attrs[id] = GladeName(type.get_object(), ResourceAsModule(resource), line)
    
        self.cache[scope_path] = attrs
        
        return attrs
    
    def add_class(self, scope, glade_file):
        self.gtk_aware_classes[scope] = glade_file

        
class GladeHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.objects = []
    
    def startElement(self, name, attrs):
        if name == 'object':
            self.objects.append((attrs['id'], attrs['class'], self._locator.getLineNumber()))