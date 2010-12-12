import pytest

from snaked.core.prefs import PySettings

def test_prefs_must_return_default_values():
    class Pref(PySettings):
        key1 = 'key1'
        key2 = 'key2'

    p = Pref()
    assert p['key1'] == 'key1'
    assert p['key2'] == 'key2'

def test_prefs_must_return_assigned_values():
    class Pref(PySettings):
        key1 = 'key1'
        key2 = 'key2'

    p = Pref()
    p.add_source('d', {})
    p['key1'] = 'key11'
    p['key2'] = None

    assert p['key1'] == 'key11'
    assert p['key2'] == None

def test_prefs_must_raise_exception_on_attributes_with_default_none_value():
    class Pref(PySettings):
        key1 = None

    p = Pref()
    with pytest.raises(KeyError):
        p['key1']

    with pytest.raises(KeyError):
        p['key2']

def test_prefs_must_provide_inclusion_check():
    class Pref(PySettings):
        key1 = 'key1'
        key2 = None

    p = Pref()
    p.add_source('d', {})
    p['key1'] = 'key11'
    p['key3'] = 'key3'
    p['key4'] = None

    assert 'key1' in p
    assert 'key2' not in p
    assert 'key3' in p
    assert 'key4' in p

def test_prefs_must_provide_its_source():
    class Pref(PySettings):
        key1 = 'key1'
        key1_doc = 'Example key'
        key2 = None
        key3 = True
        key3_doc = 'Another key'

    p = Pref()
    p.add_source('parent', {'key3': False})

    p.add_source('d', {})
    p['key1'] = 'key11'
    p['key4'] = '50'

    result = p.get_config('d', 'parent')

    assert '# Example key' in result
    assert "key1 = 'key11'" in result
    assert 'key2' not in result
    assert '# Another key' in result
    assert '# key3 = False' in result
    assert 'key4' not in result

    data = {}
    exec result in data
    assert data['key1'] == p['key1']
