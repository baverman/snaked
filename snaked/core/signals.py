from gsignals import SignalManager, Signal

class EditorSignals(SignalManager):
    editor_closed = Signal(object)
