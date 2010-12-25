import gobject
import gobject.constants
import weakref
from inspect import getmembers, ismethod

from weak import weak_connect
from util import append_attr

SSIGNAL = gobject.SIGNAL_RUN_LAST | gobject.SIGNAL_NO_RECURSE | gobject.SIGNAL_ACTION
SACTION = gobject.SIGNAL_RUN_LAST | gobject.SIGNAL_ACTION

def attach_signal_connect_info(attr, obj, func, after, idle):
    """
    Adds signal connection info to function

    Used by signal and trigger decorators
    """
    connect_params = dict(after=after, idle=idle)

    if func:
        if not getattr(func, '__call__'):
            raise Exception('Signal decorator accept callable or connect params')

        append_attr(func, attr, (obj, connect_params))
        return func
    else:
        def inner(func):
            append_attr(func, attr, (obj, connect_params))
            return func

        return inner

class Signal(object):
    """
    Unbounded signal

    Class holds signal parameters which used to construct correct GObject later.

    Instantiating signals::

        Signal() # Signal without arguments

        Signal(object, int) # Signal with two arguments

        Signal(object, return_type=int) # Signal with return type

        Signal(type=gobject.SIGNAL_RUN_FIRST) # default signal type is gobject.SIGNAL_RUN_LAST | gobject.SIGNAL_NO_RECURSE | gobject.SIGNAL_ACTION


    Unbounded signal instances can be used to mark callbacks for automatic signal connecting::

        signal = Signal()

        class Handler(object):
            @signal
            def callback(...): pass # Usual (in gobject terms) signal connection

            @signal(idle=True)
            def callback(...): pass # Connects signal with idle wrapper

            @signal(after=True)
            def callback(...): pass # sender.connect_after(callback) analog

            @signal(idle=9999)
            def callback(...): pass # idle wrapper will start callback with specified priority
    """

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
        """IDE hint"""
        raise Exception('You cannot emit unbounded signals')

    def stop_emission(self):
        """IDE hint"""
        raise Exception('You cannot stop emission of unbounded signals')


class SignalManager(object):
    """
    Wrapper for inner GObject with signals

    Example::

        class Manager(SignalManager):
            show = Signal()
            hide = Signal()

    ``Manager.show`` and ``Manager.hide`` is unbounded signals and can be used as
    decorators to callbacks. Whereas ``instance.show`` and ``instance.hide`` is bounded and
    can be used to emit signals::

        class Plugin(object):
            def __init__(self):
                self.signals = Manager()
                self.signals.connect_signals()

                self.signals.hide.emit()

            @Manager.show
            def show(self, sender):
                pass

    Inner GObject with necessary __gsignals__ is constructed during instance initialization
    """
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

        def make_signal_prop(signal):
            def inner(self):
                return BoundedSignal(self, signal)

            return property(inner)

        newdict = dict(cls.__dict__)
        signals = {}
        for sname, signal in cls.__dict__.iteritems():
            if isinstance(signal, Signal):
                signal.name = sname.replace('_', '-')
                signals[signal.name] = (signal.signal_type,
                    signal.return_type, signal.arg_types)

                newdict[sname] = make_signal_prop(signal)

        if not signals:
            return super(SignalManager, cls).__new__(cls, *args, **kwargs)

        newdict['__gsignals__'] = signals
        newdict['weak_connect'] = SignalManager.weak_connect
        newdict['connect_signals'] = SignalManager.connect_signals

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

    def connect_signals(self, obj):
        """
        Connects marked object methods
        """
        for attr, value in getmembers(obj.__class__, ismethod):
            for signal, connect_params in getattr(value, 'signals_to_connect', ()):
                id = self.weak_connect(signal, obj, attr, **connect_params)
                append_handler_to_object(obj, attr, id, self, signal.name)

    def weak_connect(self, signal, obj, attr, after, idle):
        """
        Connects unbounded signal

        @param signal: Unbounded signal
        """
        return weak_connect(self, signal.name, obj, attr, after=after, idle=idle)


class BoundedSignal(object):
    """
    This class knows about its GObject wrapper and unbounded signal name

    This allows it to emit signals. Bounded signal weakly connected to its manager so
    you can safely use it in any context
    """
    def __init__(self, manager, signal):
        self.manager = weakref.ref(manager)
        self.signal = signal

    def connect(self, obj, attr, after=False, idle=False):
        manager = self.manager()
        if manager:
            manager.weak_connect(self.signal, obj, attr, after=after, idle=idle)

    def emit(self, *args):
        manager = self.manager()
        if manager:
            return manager.emit(self.signal.name, *args)

    def stop_emission(self):
        manager = self.manager()
        if manager:
            return manager.stop_emission(self.signal.name)

def connect_external(sender_name, signal_name, after=False, idle=False):
    def inner(func):
        return attach_signal_connect_info('external_signals_to_connect',
            (sender_name, signal_name), func, after, idle)

    return inner

def connect_external_signals(obj, **kwargs):
    for attr, value in getmembers(obj.__class__, ismethod):
        for (sender_name, signal_name), connect_params in getattr(value, 'external_signals_to_connect', ()):
            sender = kwargs[sender_name]
            id = weak_connect(sender, signal_name, obj, attr, **connect_params)
            append_handler_to_object(obj, attr, id, sender, signal_name, sender_name)

def append_handler_to_object(obj, attr, handler_id, sender, signal_name, sender_name=None):
    name = attr + '_handler'
    if not hasattr(obj, name):
        setattr(obj, name, HandlerHolder())

    getattr(obj, name).add(handler_id, sender, signal_name, sender_name)

def connect_all(obj, *signal_managers, **external_senders):
    [s.connect_signals(obj) for s in signal_managers]

    if external_senders:
        connect_external_signals(obj, **external_senders)

class Handler(object):
    def __init__(self, handler_id, sender, signal_name, sender_name):
        self.id = handler_id
        self.sender = weakref.ref(sender)
        self.signal_name = signal_name
        self.sender_name = sender_name

    def is_match(self, sender, sender_name, signal_name):
        result = True

        result = result and (sender == None or self.sender() is sender)
        result = result and (sender_name == None or self.sender_name == sender_name)
        result = result and (signal_name == None or self.signal_name == signal_name)

        return result

    def block(self):
        sender = self.sender()
        if sender:
            sender.handler_block(self.id)

    def unblock(self):
        sender = self.sender()
        if sender:
            sender.handler_unblock(self.id)


class HandlerHolder(object):

    def __init__(self):
        self.handlers = []

    def add(self, id, sender, signal_name, sender_name=None):
        self.handlers.append(Handler(id, sender, signal_name, sender_name))

    def block(self):
        try:
            (handler,) = self.handlers
            handler.block()
        except ValueError:
            raise Exception('There are several signals connected to callback')

    def unblock(self):
        try:
            (handler,) = self.handlers
            handler.unblock()
        except ValueError:
            raise Exception('There are several signals connected to callback')

    @property
    def id(self):
        try:
            (handler,) = self.handlers
            return handler.id
        except ValueError:
            raise Exception('There are several signals connected to callback')

    def __call__(self, sender=None, sender_name=None, signal_name=None):
        handler = None
        for h in self.handlers:
            if h.is_match(sender=sender, sender_name=sender_name, signal_name=signal_name):
                if handler:
                    raise Exception('Match returns several handlers')
                else:
                    handler = h

        return handler
