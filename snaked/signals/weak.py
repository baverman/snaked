import weakref
from gobject import idle_add

class WeakCallback(object):
    """
    Weak callback functor which disconnects on real callback deletion
    
    Magic goes here. It allows to skip accurate manual object disposion by brokening
    cyclic reference beetween sender and callback. Let python gc to work.
    
    Also it can wrap callback in idle_add with specified priority.
    
    Important note! Object and its callback attribute are passed separately.
    Because bounded methods are too weak.
    """
    def __init__(self, obj, attr, idle):
        self.wref = weakref.ref(obj)
        self.callback_attr = attr
        self.gobject_token = None
        self.dbus_token = None
        self.idle = idle

    def __call__(self, *args, **kwargs):
        obj = self.wref()
        if obj:
            # object still alive so calling method 
            attr = getattr(obj, self.callback_attr)
            
            if self.idle is False or self.idle is None:
                return attr(*args, **kwargs)
            elif self.idle is True:
                idle_add(attr, *args, **kwargs)
            else:
                idle_add(attr, priority=self.idle, *args, **kwargs)
                    
        elif self.gobject_token:
            sender = args[0]
            sender.disconnect(self.gobject_token)
            self.gobject_token = None
        elif self.dbus_token:
            self.dbus_token.remove()
            self.dbus_token = None
            
        return False


def weak_connect(sender, signal, connector, attr, idle=False, after=False):
    """
    Function to connect some GObject with weak callback
    """
    wc = WeakCallback(connector, attr, idle)
    
    if after:
        wc.gobject_token = sender.connect_after(signal, wc)
    else:
        wc.gobject_token = sender.connect(signal, wc)

    #print "Connected", sender, signal, connector, attr, idle, after

    return wc.gobject_token
