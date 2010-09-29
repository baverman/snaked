import gobject
import gobject.constants
import weakref

from weak import weak_connect

SSIGNAL = gobject.SIGNAL_RUN_LAST | gobject.SIGNAL_NO_RECURSE | gobject.SIGNAL_ACTION
SACTION = gobject.SIGNAL_RUN_LAST | gobject.SIGNAL_ACTION

    
class Signal(object):
    def __init__(self, *signal_args, **kwargs):
        allowed_named_arguments = set(('type', 'return_type'))
        if not all(r in allowed_named_arguments for r in kwargs.keys()): 
            raise Exception('Signal constructor takes only `type` and `return_type` named arguments')
        
        self.signal_type = kwargs.get('type', SSIGNAL)
        self.return_type = kwargs.get('return_type', None)
        self.arg_types = tuple(signal_args)
        self.name = None

    def __call__(self, func=None, after=False, idle=False):
        return attach_signal_connect_info('signals_to_connect', self, func, after, idle)
            
    def emit(self):
        raise Exception('You cannot emit unbounded signals')


class SignalManager(object):
    registered_classes = {}

    def __new__(cls, *args, **kwargs):
        try:
            newcls = SignalManager.registered_classes[cls]
            obj = newcls.__new__(newcls, *args, **kwargs)
            gobject.GObject.__init__(obj)
            newcls.__init__(obj, *args, **kwargs)

            return obj
        except KeyError:
            pass

        signals = {}
        for sname, signal in cls.__dict__.iteritems():
            if isinstance(signal, Signal):
                signal.name = sname.replace('_', '-')
                signals[signal.name] = (signal.signal_type,
                    signal.return_type, signal.arg_types)
        
        if not signals:
            return super(SignalManager, cls).__new__(cls, *args, **kwargs)

        newdict = dict(cls.__dict__)
        
        newdict['__gsignals__'] = signals
        newdict['weak_connect'] = SignalManager.weak_connect

        for k, v in newdict.iteritems():
            if hasattr(v, 'im_func'):
                newdict[k] = v.im_func

        newcls = type(cls.__name__, (gobject.GObject,), newdict)
        gobject.type_register(newcls)
        SignalManager.registered_classes[cls] = newcls
        
        obj = newcls.__new__(newcls, *args, **kwargs)
        gobject.GObject.__init__(obj)
        newcls.__init__(obj, *args, **kwargs)

        return obj

    def weak_connect(self, signal, obj, attr, after=False, idle=False):
        return weak_connect(self, signal, obj, attr, after=after, idle=idle)


class BoundedSignal(object):
    def __init__(self, manager, signal):
        self.manager = weakref.ref(manager)
        self.signal = signal

    def emit(self, *args):
        manager = self.manager()
        if manager: 
            return manager.sender.emit(self.signal.name, *args)


class Handler(object):
    def __init__(self, handler_id, sender):
        self.id = handler_id
        self.sender = weakref.ref(sender)
        
    def block(self):
        sender = self.sender()
        if sender:
            sender.handler_block(self.id)
        
    def unblock(self):
        sender = self.sender()
        if sender:
            sender.handler_unblock(self.id)
