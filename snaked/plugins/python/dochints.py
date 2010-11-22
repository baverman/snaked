import re

from .ropehints import HintProvider

class DocStringHintProvider(HintProvider):
    """Allows to hint functions/method parameters and return values types through doc strings

    This is build-in provider so you have no do any addition steps to enable it.

    Hints can be provided using Sphinx syntax::

        def func(text):
            '''
            :type text: str
            :rtype: str
            '''
            # now in func body 'text' parameter's type is resolved into 'str'

        # And all rest code now knows ``func`` return type is also 'str'

    """
    def __init__(self, project):
        super(DocStringHintProvider, self).__init__(project)
        self.cache = {}

    def get_function_param_type(self, pyfunc, name):
        """Resolve function's parameters types from doc string

        :type pyfunc: rope.base.pyobjectsdef.PyFunction
        """
        scope_path = self.get_scope_path(pyfunc.get_scope())
        try:
            params = self.cache[scope_path]
        except KeyError:
            #print 'getting param types for', scope_path
            params = self.cache[scope_path] = self.get_params_from_pydoc(pyfunc)

        return params.get(name, None)

    def get_params_from_pydoc(self, pyfunc):
        result = {}

        doc = pyfunc.get_doc()
        if doc:
            match = re.search(':rtype:\s*([.\w]+)', doc)
            if match:
                type_name = match.group(1)
                pyname = self.get_type(type_name, pyfunc.get_scope())
                if pyname:
                    result['return'] = pyname.get_object()

            for m in re.finditer(':type\s*(\w+):\s*([.\w]+)', doc):
                type_name = m.group(2)
                pyname = self.get_type(type_name, pyfunc.get_scope())
                if pyname:
                    result[m.group(1)] = pyname.get_object()

        return result
