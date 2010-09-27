from gsignals import SignalManager, Signal

class EditorSignals(SignalManager):
    editor_closed = Signal(object)
    request_to_open_file = Signal(str, return_type=object)
    update_title = Signal(return_type=str)