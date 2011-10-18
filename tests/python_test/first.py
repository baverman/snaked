import pytest
import os.path

def test_first():
    pass

def test_second():
    print 'test-second' + '-output'
    assert 2 == 1

@pytest.mark.xfail
def test_third():
    raise NotImplementedError()

def test_fourth():
    os.path.join(None, None)
