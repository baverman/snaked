import pytest

from snaked.plugins.external_tools.parser import parse, ParseException

data1 = """
#Comment
tool "sphinx _make" for "project-doc" to-console
    cd doc
    make html

tool "sphinx _clean" for "project-doc" to-feedback
    cd doc

    make clean

tool "run" for "python, python-script" from-buffer to-console
    python $FILENAME
"""

def test_external_tool_parsing():
    tools = parse(data1)

    t = tools[0]
    assert t.name == 'sphinx _make'
    assert t.context == ['project-doc']
    assert t.input == None
    assert t.output == 'to-console'
    assert t.script == "    cd doc\n    make html\n"

    t = tools[1]
    assert t.name == 'sphinx _clean'
    assert t.context == ['project-doc']
    assert t.input == None
    assert t.output == 'to-feedback'
    assert t.script == "    cd doc\n\n    make clean\n"

    t = tools[2]
    assert t.name == 'run'
    assert t.context == ['python', 'python-script']
    assert t.input == 'from-buffer'
    assert t.output == 'to-console'
    assert t.script == "    python $FILENAME"

def test_invalid_tool_name_parsing():
    data = """
tool sss
    cd wow
    """

    try:
        parse(data)
        pytest.fail('Must raise ParseException')
    except ParseException, e:
        assert 'tool name' in str(e)

def test_garbage_in_tool_definition():
    data = """
tool "sss" for sss
    cd wow
    """

    try:
        parse(data)
        pytest.fail('Must raise ParseException')
    except ParseException, e:
        assert 'for sss' in str(e)
