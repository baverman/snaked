from snaked.core.titler import create_fsm, add_title_handler

def hempty(name):
    return None

def hid(name):
    return name

def hq(name):
    return '"%s"' % ( name if name else None)

add_title_handler('hid', hid)
add_title_handler('hq', hq)
add_title_handler('hempty', hempty)

def test_simple_handler():
    fsm = create_fsm("%hq")
    result = fsm('aaa')
    assert result == '"aaa"'

def test_no_handler():
    fsm = create_fsm("str")
    result = fsm('aaa')
    assert result == 'str'

def test_alt_handler():
    fsm = create_fsm("{%hid|sss}")

    result = fsm(None)
    assert result == 'sss'

    result = fsm('aaa')
    assert result == 'aaa'

def test_alt_handler_with_additional_symbols():
    fsm = create_fsm("{%hid:|sss}")

    result = fsm(None)
    assert result == 'sss'

    result = fsm('aaa')
    assert result == 'aaa:'

def test_alt_handler_with_empty_section():
    fsm = create_fsm("{%hid|}")

    result = fsm(None)
    assert result == ''

def test_complex():
    fsm = create_fsm("[{%hid-|}%hq/{%hempty|%hid|nop}] RO")

    result = fsm(None)
    assert result == '["None"/nop] RO'

    result = fsm('aaa')
    assert result == '[aaa-"aaa"/aaa] RO'