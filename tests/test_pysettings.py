from snaked.core.prefs import PySettings

def make_settings(**kwargs):
    return PySettings(dict((k, (v, '')) for k,v in kwargs.items()))

def test_prefs_must_return_default_values():
    p = make_settings(key1='key1', key2='key2')
    assert p['key1'] == 'key1'
    assert p['key2'] == 'key2'

def test_prefs_must_return_parent_values():
    p = make_settings(key1='key1', key2='key2')
    pp = PySettings(parent=p)

    p['key1'] = 20

    assert pp['key1'] == 20
    assert pp['key2'] == 'key2'

def test_prefs_must_return_assigned_values():
    p = make_settings(key1='key1', key2='key2')
    p['key1'] = 'key11'
    p['key2'] = None

    assert p['key1'] == 'key11'
    assert p['key2'] == None

def test_prefs_must_provide_its_source():
    p = make_settings(a=True, b=10, c=False)

    p['a'] = False
    p['b'] = 10

    result = p.get_config()

    assert 'a = False' in result
    assert '# b = 10' in result
    assert '# c = False' in result

def test_prefs_parent_config_override():
    p1 = make_settings(a=True, b=10, c=False)
    p2 = PySettings(parent=p1)

    p1['a'] = False

    p1['b'] = 1
    p2['b'] = 10

    p2['c'] = False

    result = p2.get_config()

    assert 'a = False' in result
    assert 'b = 10' in result
    assert '# c = False' in result