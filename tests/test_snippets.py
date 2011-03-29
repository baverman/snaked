import os.path
ROOT = os.path.dirname(os.path.dirname(__file__))

from snaked.plugins.snippets.parser import parse_snippets_from

python_snippets = os.path.join(ROOT, 'snaked', 'plugins', 'snippets',
    'snippets', 'python.snippets')

def get_slice(body, start, end):
    return body[start:end]

def test_parse_snippets_from():
    result = parse_snippets_from(python_snippets)

    assert 'imp' in result
    assert result['imp'].comment == 'Module import'
    assert result['imp'].snippet == 'imp'
    assert result['imp'].body == ['import ${1:module}']

    assert 'try Try/Except' in result
    assert result['try Try/Except'].snippet == 'try'

    assert 'try Try/Except/Else' in result
    assert result['try Try/Except/Else'].snippet == 'try'

def test_snippet_body_and_offsets():
    result = parse_snippets_from(python_snippets)
    body, stop_offsets, insert_offsets = result['cl'].get_body_and_offsets()

    assert get_slice(body, *stop_offsets[1]) == 'ClassName'
    assert get_slice(body, *stop_offsets[2]) == 'object'
    assert get_slice(body, *stop_offsets[3]) == ''
    assert get_slice(body, *stop_offsets[4]) == 'super(ClassName, self).__init__()'

    assert get_slice(body, *stop_offsets[1]) == 'ClassName'

def test_snippet_body_and_offsets2():
    result = parse_snippets_from(python_snippets)
    body, stop_offsets, insert_offsets = result['try Try/Except'].get_body_and_offsets()

    assert get_slice(body, *stop_offsets[1]) == 'pass'
    assert get_slice(body, *stop_offsets[2]) == 'Exception'
    assert get_slice(body, *stop_offsets[3]) == 'e'
    assert get_slice(body, *stop_offsets[4]) == 'raise e'

    assert get_slice(body, *stop_offsets[3]) == 'e'

def test_snippet_body_and_offsets3(tmpdir):
    snipp = tmpdir.join('snippet')
    snipp.write('''snippet set
\t@${1:propname}.setter
\tdef $1(self, value):
\t\tself._$1 = value''')

    result = parse_snippets_from(str(snipp))
    body, stop_offsets, insert_offsets = result['set'].get_body_and_offsets()

    assert get_slice(body, *stop_offsets[1]) == 'propname'
    assert insert_offsets[1] == [(21, 29), (51, 59)]