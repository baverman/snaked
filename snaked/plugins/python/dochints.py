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

    def get_function_params(self, scope_path, pyfunc):
        """:type pyfunc: rope.base.pyobjectsdef.PyFunction"""

        result = {}
        doc = pyfunc.get_doc()
        if doc:
            match = re.search(':rtype:\s*([.\w]+)', doc)
            if match:
                type_name = match.group(1)
                pyname = self.get_type(type_name, pyfunc.get_scope())
                if pyname:
                    result['return'] = pyname.get_object()

            param_names = pyfunc.get_param_names(False)
            for m in re.finditer(':type\s*(\w+):\s*([.\w]+)', doc):
                try:
                    idx = param_names.index(m.group(1))
                except ValueError:
                    continue

                type_name = m.group(2)
                pyname = self.get_type(type_name, pyfunc.get_scope())
                if pyname:
                    result[idx] = pyname.get_object()

        return result
