author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Edit and Select'
desc = 'Various edit shortcuts'

import weakref
import gtk

last_smart_selections = weakref.WeakKeyDictionary()

def init(injector):
    injector.bind_accel('editor-active', 'delete-line', '_Edit/_Delete line', '<ctrl>d', delete_line)

    injector.bind_accel('editor-active', 'smart-select', '_Edit/Smart _select', '<alt>w', smart_select)
    injector.bind_accel('editor-with-selection', 'smart-unselect', '_Edit/Smart _unselect',
        '<shift><alt>w', smart_unselect)

    injector.bind_accel('editor-active', 'show_offset', '_Tools/Show offset and column',
        '<ctrl><alt>o', show_offset)

    injector.bind_accel('editor-with-selection', 'wrap-text', '_Edit/_Wrap block', '<alt>f', wrap_text)

    injector.bind_accel('editor-with-selection', 'move-selection-left',
        '_Edit/Move selection _left', '<alt>Left', move_word_left)
    injector.bind_accel('editor-with-selection', 'move-selection-right',
        '_Edit/Move selection _right', '<alt>Right', move_word_right)

    from snaked.core.prefs import add_option
    add_option('DOUBLE_BRACKET_MATCHER', True, "Enable custom bracket matcher")
    add_option('COPY_DELETED_LINE', True, "Put deleted line into clipboard")

def editor_created(editor):
    if editor.conf['DOUBLE_BRACKET_MATCHER']:
        from bracket_matcher import attach
        attach(editor)

def delete_line(editor):
    from util import get_line_bounds, line_is_empty

    bounds = get_line_bounds(editor.cursor)
    if not line_is_empty(editor.cursor) and editor.conf['COPY_DELETED_LINE']:
        clipboard = editor.view.get_clipboard(gtk.gdk.SELECTION_CLIPBOARD)
        editor.buffer.select_range(*bounds)
        editor.buffer.copy_clipboard(clipboard)

    editor.buffer.begin_user_action()
    editor.buffer.delete(*bounds)
    editor.buffer.end_user_action()

def update_last_smart_select(editor, start, end):
    start, end = start.get_offset(), end.get_offset()
    if editor in last_smart_selections and last_smart_selections[editor]:
        os, oe = last_smart_selections[editor][0]
        if start <= os and end >= oe:
            last_smart_selections[editor].insert(0, (start, end))
            return

    last_smart_selections[editor] = [(start, end)]

def smart_select(editor):
    from smart_select import get_smart_select

    if editor.buffer.get_has_selection():
        update_last_smart_select(editor, *editor.buffer.get_selection_bounds())
    else:
        update_last_smart_select(editor, editor.cursor, editor.cursor)

    start, end = get_smart_select(editor)
    editor.buffer.select_range(end, start)

def smart_unselect(editor):
    if editor not in last_smart_selections or not last_smart_selections[editor]:
        editor.message('Unselect what?')
        return

    start, end = map(gtk.TextIter.get_offset, editor.buffer.get_selection_bounds())
    ts, te = last_smart_selections[editor].pop(0)

    if ts >= start and te <= end:
        editor.buffer.select_range(*map(editor.buffer.get_iter_at_offset, (te, ts)))
    else:
        last_smart_selections[editor][:] = []
        editor.message('Nothing to unselect')

def show_offset(editor):
    editor.message('offset: %d\ncolumn: %d' % (
        editor.cursor.get_offset(), editor.cursor.get_line_offset()), 3000)

def wrap_text(editor):
    buf = editor.buffer
    import textwrap, re
    from util import get_whitespace

    start, end = buf.get_selection_bounds()
    start.order(end)
    if end.starts_line():
        end.backward_visible_cursor_position()

    si = ''
    second_line = start.copy()
    second_line.set_line(start.get_line() + 1)
    if second_line.get_offset() < end.get_offset():
        si = get_whitespace(second_line)

    text = buf.get_text(start, end).decode('utf-8')
    text = re.sub('(?m)^\s+', '', text)
    text = textwrap.fill(text, subsequent_indent=si ,width=editor.view.get_right_margin_position())

    buf.begin_user_action()
    buf.place_cursor(end)
    buf.delete(start, end)
    buf.insert_at_cursor(text)
    buf.end_user_action()

def move_word(buf, fromiter, tomark):
    toiter = fromiter.copy()
    toiter.forward_char()

    text = fromiter.get_text(toiter)

    buf.begin_user_action()
    buf.delete(fromiter, toiter)
    buf.insert(buf.get_iter_at_mark(tomark), text)
    buf.end_user_action()

def move_word_left(editor):
    buf = editor.buffer
    start, end = map(gtk.TextIter.copy, buf.get_selection_bounds())
    start.order(end)

    if not start.backward_char():
        editor.message('You are already at begin of file')
        return

    move_word(buf, start, buf.create_mark(None, end))

    start, end = buf.get_selection_bounds()
    start.order(end)
    end.backward_char()
    buf.select_range(start, end)

def move_word_right(editor):
    buf = editor.buffer
    start, end = map(gtk.TextIter.copy, buf.get_selection_bounds())
    start.order(end)

    if end.is_end():
        editor.message('You are already at end of file')
        return

    move_word(buf, end, buf.create_mark(None, start))
