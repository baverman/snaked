import xml.sax.handler
import rope.base.pynames

import gobject

from .ropehints import HintProvider

def add_gtk_support(composite_provider):
    existing_modules = composite_provider.project.prefs['extension_modules']

    for m in ('gtk._gtk', 'gtk.gdk', 'gobject._gobject', 'pango'):
        if m not in existing_modules:
            existing_modules.append(m)

    composite_provider.project.prefs['extension_modules'] = existing_modules

    return composite_provider.add_hint_provider(PyGtkHintProvider(composite_provider.project))


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

    def get_pygtk_class_name(self, gtk_class_name):
        return gtk_class_name.replace('Gtk', 'gtk.', 1) + '()'

    def process_glade(self, scope_path, force=False):
        glade_file, processed = self.gtk_aware_classes[scope_path]
        if processed and not force:
            return

        resource = self.project.get_resource(glade_file)

        handler = GladeHandler()
        xml.sax.parseString(open(resource.real_path).read(), handler)

        attrs = {}
        for id, cls, line in handler.objects:
            type = self.get_type(self.get_pygtk_class_name(cls))
            attrs[id] = GladeName(type.get_object(), ResourceAsModule(resource), line)

        self.cache[scope_path] = attrs

        for name, (cls, signal) in handler.signals.iteritems():
            self.handlers.setdefault(scope_path, {})[name] = cls, signal

        self.gtk_aware_classes[scope_path] = glade_file, True

    def get_class_attributes(self, scope_path, pyclass, attrs):
        attrs = {}
        if scope_path in self.gtk_aware_classes:
            self.process_glade(scope_path)
            for k, v in self.cache[scope_path].iteritems():
                attrs[k] = v

        return attrs

    def add_class(self, scope, glade_file):
        self.gtk_aware_classes[scope] = glade_file, False

    def get_function_param_type(self, pyfunc, name):
        """Resolve function's parameters types from doc string

        :type pyfunc: rope.base.pyobjectsdef.PyFunction
        """

        scope_path = self.get_scope_path(pyfunc.get_scope())
        try:
            params = self.func_cache[scope_path]
        except KeyError:
            class_scope = scope_path.rpartition('.')[0]
            if class_scope not in self.gtk_aware_classes:
                params = {}
            else:
                self.process_glade(class_scope)
                params = self.get_params_for_handler(class_scope, pyfunc)

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