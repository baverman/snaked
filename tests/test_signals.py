from snaked.signals import SignalManager, Signal

class Manager(SignalManager):
    get_value = Signal(return_type=object)

def test_multiple_connected_handler_must_be_allowed_to_return_value():
    m = Manager()

    vals = [1, False]

    def f1(m):
        if vals[0]:
            m.stop_emission('get-value')
            return vals[0]

    def f2(m):
        if vals[1]:
            m.stop_emission('get-value')
            return vals[1]

    m.connect('get-value', f1)
    m.connect('get-value', f2)

    val = m.get_value.emit()
    assert val == 1

    vals = [False, 2]
    val = m.get_value.emit()
    assert val == 2
