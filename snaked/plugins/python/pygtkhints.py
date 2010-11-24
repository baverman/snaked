import re
import os

import xml.sax.handler
import rope.base.pynames

import gobject

from .ropehints import HintProvider, get_attribute_scope_path

pydoc_glade_file_matcher = re.compile('(?m)^.*glade-file\s*:(.*)$')

def add_gtk_support(composite_provider):
    add_gtk_extension_modules(composite_provider.project)
    return composite_provider.add_hint_provider(PyGtkHintProvider(composite_provider.project))

def add_gtk_extension_modules(project):
    existing_modules = project.prefs['extension_modules']
    for m in ('gtk._gtk', 'gtk.gdk', 'gobject._gobject', 'pango'):
        if m not in existing_modules:
            existing_modules.append(m)

    project.prefs['extension_modules'] = existing_modules


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
        self.func_cache = {}
        self.handlers = {}
        self.processed_files = {}

    def get_pygtk_class_name(self, gtk_class_name):
        return gtk_class_name.replace('Gtk', 'gtk.', 1) + '()'

    def process_glade(self, scope_path, glade_resource, force=False):
        glade_file = glade_resource.real_path
        processed = self.processed_files.get(glade_file, False)
        if processed and not force:
            return

        handler = GladeHandler()
        xml.sax.parseString(open(glade_file).read(), handler)

        attrs = {}
        for id, cls, line in handler.objects:
            type = self.get_type(self.get_pygtk_class_name(cls))
            attrs[id] = GladeName(type.get_object(), ResourceAsModule(glade_resource), line)

        self.cache[scope_path] = attrs

        for name, (cls, signal) in handler.signals.iteritems():
            self.handlers.setdefault(scope_path, {})[name] = cls, signal

        self.gtk_aware_classes[scope_path] = glade_file

    def get_glade_file_for_class(self, scope_path, pyclass):
        try:
            return self.gtk_aware_classes[scope_path]
        except KeyError:
            pass

        doc = pyclass.get_doc()
        if doc:
            match = pydoc_glade_file_matcher.search(doc)
            if match:
                filename = match.group(1).strip()
                if filename.startswith('/'):
                    return filename[1:]
                else:
                    return os.path.join(os.path.dirname(pyclass.get_module().resource.path), filename)

        return None

    def get_class_attributes(self, scope_path, pyclass, attrs):
        attrs = {}
        glade_file = self.get_glade_file_for_class(scope_path, pyclass)
        if glade_file:
            glade_resource = pyclass.get_module().resource.project.get_file(glade_file)
            self.process_glade(scope_path, glade_resource)
            for k, v in self.cache[scope_path].iteritems():
                attrs[k] = v

        return attrs

    def add_class(self, scope, glade_file):
        self.gtk_aware_classes[scope] = glade_file

    def get_function_param_type(self, pyfunc, name):
        """Resolve function's parameters types from doc string

        :type pyfunc: rope.base.pyobjectsdef.PyFunction
        """
        scope_path = self.get_scope_path(pyfunc.get_scope())
        try:
            params = self.func_cache[scope_path]
        except KeyError:
            pyclass = pyfunc.parent
            class_scope = get_attribute_scope_path(pyclass)
            glade_file = self.get_glade_file_for_class(scope_path, pyclass)

            if glade_file:
                glade_resource = pyclass.get_module().resource.project.get_file(glade_file)
                self.process_glade(scope_path, glade_resource)
                params = self.get_params_for_handler(class_scope, pyfunc)
            else:
                params = {}

            self.func_cache[scope_path] = params

        return params.get(name, None)

    def get_params_for_handler(self, class_scope, pyfunc):
        """:type pyfunc: rope.base.pyobjectsdef.PyFunction"""
        try:
            cls, signal = self.handlers[class_scope][pyfunc.get_name()]
        except KeyError:
            return {}

        attrs = {}

        names = pyfunc.get_param_names(False)
        if pyfunc.get_kind() in ('method', 'classmethod'):
            names = names[1:]

        if names:
            attrs[names[0]] = self.get_type(self.get_pygtk_class_name(cls)).get_object()
            names = names[1:]

        if names:
            for i, t in enumerate(gobject.signal_query(signal, str(cls))[-1]):
                try:
                    tname = self.get_type(self.get_pygtk_class_name(t.name))
                    if tname:
                        attrs[names[i]] = tname.get_object()
                    else:
                        attrs[names[i]] = None
                except IndexError:
                    break

        return attrs


class GladeHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.objects = []
        self.signals = {}
        self.current_object_class = None

    def startElement(self, name, attrs):
        if name == 'object':
            self.objects.append((attrs['id'], attrs['class'], self._locator.getLineNumber()))
            self.current_object_class = attrs['class']
        elif name == 'signal':
            if self.current_object_class:
                self.signals[attrs['handler']] = self.current_object_class, attrs['name']

    def endElement(self, name):
        if name == 'object':
            self.current_object_class = None