import weakref
import gtk

def init(injector):
    injector.add_context('spot-manager', 'window', lambda w: w.manager.spot_manager)
    #injector.add_context('edit-spot', 'editor-active', spot_context('edit'))
    #injector.add_context('master-spot', 'editor-active', spot_context('master'))
    injector.add_context('regular-spot', 'editor-active', spot_context('regular'))

    injector.bind(('spot-manager', 'editor-active', 'regular-spot'), 'goto-last-spot',
        'Edit/Goto last spot#70', Manager.goto_last).to('<Alt>q')

    #injector.bind_accel(('spot-manager', 'editor-active', 'edit-spot'), 'goto-last-spot',
    #    '_Edit/Goto last edit spot', '<Alt>q', Manager.goto_last, 5)

    injector.bind(('spot-manager', 'editor-active'), 'goto-next-spot',
        'Edit/Goto next spot', Manager.goto_next_prev, True).to('<ctrl>bracketright')

    injector.bind(('spot-manager', 'editor-active'), 'goto-prev-spot',
        'Edit/Goto prev spot', Manager.goto_next_prev, False).to('<ctrl>bracketleft')

    #injector.bind_accel(('spot-manager', 'editor-active', 'master-spot'), 'goto-last-spot',
    #    '_Edit/Goto last master spot', '<Alt>q', Manager.goto_last, 10)

    #injector.bind_accel(('spot-manager', 'editor-active'), 'add-master-spot',
    #    '_Edit/Add master spot', '<Alt>s', Manager.add_master_spot)


    injector.on_ready('buffer-created', buffer_created)
    injector.on_ready('editor', editor_opened)
    injector.on_done('editor', editor_closed)

def spot_context(spot_type):
    def inner(editor):
        new_spot = EditorSpot(editor, spot_type)
        spot = editor.window.manager.spot_manager.get_last(new_spot, None, spot_type)
        if spot:
            return spot, new_spot
        else:
            return None

    return inner

def buffer_created(buf):
    buf.connect('changed', on_buffer_changed)
    buf.is_changed = False

def on_buffer_changed(buf):
    buf.is_changed = True

def editor_opened(editor):
    editor.view.connect('move-cursor', on_textview_move_cursor)

def editor_closed(editor):
    editor.window.manager.spot_manager.remove_invalid_spots(editor=editor)

SAFE_MOVEMENTS = set((gtk.MOVEMENT_VISUAL_POSITIONS, gtk.MOVEMENT_WORDS,
    gtk.MOVEMENT_LOGICAL_POSITIONS, gtk.MOVEMENT_DISPLAY_LINE_ENDS))

def on_textview_move_cursor(view, step_size, count, extend_selection):
    if view.get_buffer().is_changed and step_size not in SAFE_MOVEMENTS:
        editor = view.editor_ref()
        editor.window.manager.spot_manager.add(editor)

class Manager(object):
    def __init__(self):
        self.history = []

    def add_master_spot(self, editor):
        self.add(editor, 'master')
        editor.message('Master spot added', 'done')

    def add(self, editor, spot_type=None):
        #if not spot_type and editor.buffer.is_changed:
        #    spot_type = 'edit'

        editor.buffer.is_changed = False
        self.add_to_history(EditorSpot(editor, spot_type))

    def remove_invalid_spots(self, spot=None, editor=None):
        result = []
        for i, s in enumerate(self.history):
            if i > 30 or (editor and s.editor() is editor) or not s.is_valid() or s.similar_to(spot):
                s.remove()
            else:
                result.append(s)

        self.history[:] = result

    def add_to_history(self, spot):
        self.remove_invalid_spots(spot=spot)
        self.history.insert(0, spot)

    def goto_last(self, editor, spots):
        if spots:
            spot, new_spot = spots
            spot.goto(editor)
            self.add_to_history(new_spot)
        else:
            editor.message('Spot history is empty', 'warn')

    def get_last(self, exclude_spot=None, exclude_editor=None, spot_type=None):
        spot_type = spot_type or 'regular'
        for s in self.history:
            if s.is_valid() and not s.similar_to(exclude_spot) \
                    and s.editor() is not exclude_editor and s.type == spot_type:
                return s

        return None

    def goto_next_prev(self, editor, is_next):
        current_spot = EditorSpot(editor)
        if is_next:
            seq = self.history
        else:
            seq = reversed(self.history)

        prev_spot = None
        for s in (s for s in seq if s.is_valid()):
            if s.similar_to(current_spot):
                if prev_spot:
                    prev_spot.goto(editor)
                else:
                    editor.message('No more spots to go', 'warn')
                return

            prev_spot = s

        spot = self.get_last(current_spot)
        if spot:
            self.goto_last(editor, (spot, current_spot))
        else:
            self.goto_last(editor, None)


class EditorSpot(object):
    def __init__(self, editor, spot_type=None):
        self.editor = weakref.ref(editor)
        self.mark = editor.buffer.create_mark(None, editor.cursor)
        self.type = spot_type or 'regular'

    @property
    def iter(self):
        return self.mark.get_buffer().get_iter_at_mark(self.mark)

    def is_valid(self):
        return self.editor() and not self.mark.get_deleted()

    def similar_to(self, spot):
        return spot and self.mark.get_buffer() is spot.mark.get_buffer() \
            and abs(self.iter.get_line() - spot.iter.get_line()) < 7

    def remove(self):
        editor = self.editor()
        if editor:
            editor.buffer.delete_mark(self.mark)
            del self.mark

    def goto(self, back_to=None):
        editor = self.editor()
        editor.buffer.place_cursor(self.iter)
        editor.clear_cursor()

        if editor is back_to:
            editor.scroll_to_cursor()
        else:
            editor.view.scroll_mark_onscreen(editor.buffer.get_insert())
            editor.focus()

