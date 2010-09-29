from signals import *

class Signals(SignalManager):
    foo = Signal(int)

    def __init__(self, num):
        self.weak_connect('foo', self, 'on_foo')
        self.emit('foo', num)

    def on_foo(self, sender, num):
        print num

s1 = Signals(5)
s2 = Signals(10)
