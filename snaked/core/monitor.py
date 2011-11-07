import gio
import glib
import weakref

def init(injector):
    injector.on_ready('buffer-loaded', buffer_loaded)
    injector.on_done('buffer', buffer_closed)
    injector.on_ready('manager', store_manager_ref)

def buffer_loaded(buf):
    monitor = gio.File(path=buf.uri).monitor(gio.FILE_MONITOR_SEND_MOVED)
    monitor.connect('changed', on_file_changed, weakref.ref(buf))
    buf.monitor = monitor

def buffer_closed(buf):
    buf.monitor.cancel()
    del buf.monitor

def store_manager_ref(manager):
    global manager_ref
    manager_ref = weakref.ref(manager)

collected_file_changes = {}
timer_id = [None]
manager_ref = None

def changes_done():
    changed = []
    deleted = []
    for buf, event in collected_file_changes.items():
        buf = buf()
        if event == 'changed':
            try:
                text = get_new_content(buf)
            except:
                import traceback
                traceback.print_exc()
                continue

            if text is not None:
                changed.append(buf)
                update_buffer_content(buf, text)

        elif event == 'deleted':
            deleted.append(buf)

    for window in manager_ref().get_windows():
        changed_buffers = []
        for e in window.editors:
            if e.buffer in changed:
                changed_buffers.append(e.buffer)
            elif e.buffer in deleted:
                e.message('File deleted', 'warn', 0)

        if changed_buffers:
            message = 'External change detected:\n'
            message += '\n'.join(r.uri for r in changed_buffers)
            message += '\nOriginal content stored in an undo history.'
            window.message(message, 'warn', 0)

    collected_file_changes.clear()
    timer_id[0] = None

def get_new_content(buf):
    text = open(buf.uri).read().decode(buf.encoding)
    buf_text = buf.get_text(*buf.get_bounds()).decode('utf-8')
    if text != buf_text:
        return text

    return None

def update_buffer_content(buf, text):
    buf.begin_user_action()
    buf.set_text(text)
    buf.set_modified(False)
    buf.end_user_action()
    buf.is_changed = False

def on_file_changed(monitor, changed_file, other_file, event_type, buf):
    if getattr(monitor, 'saved_by_snaked', False):
        monitor.saved_by_snaked = False
        return

    if event_type == gio.FILE_MONITOR_EVENT_CHANGES_DONE_HINT:
        collected_file_changes[buf] = 'changed'
    elif event_type == gio.FILE_MONITOR_EVENT_DELETED:
        collected_file_changes[buf] = 'deleted'

    if timer_id[0]:
        glib.source_remove(timer_id[0])

    timer_id[0] = glib.timeout_add(1000, changes_done)
