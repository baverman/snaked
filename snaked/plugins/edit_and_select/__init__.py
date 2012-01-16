author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Edit and Select'
desc = 'Various edit shortcuts'

import weakref
import gtk
from uxie.floating import TextFeedback

last_smart_selections = weakref.WeakKeyDictionary()

def init(injector):
    injector.add_context('editor-with-cursor-in-string', 'editor', in_string)

    injector.bind('editor-active', 'delete-line', 'Edit/_Delete line#20', delete_line).to('<ctrl>d')

    injector.bind('editor-active', 'smart-select', 'Edit/Smart _select', smart_select).to('<alt>w')
    injector.bind('editor-with-selection', 'smart-unselect', 'Edit/Smart _unselect',
        smart_unselect).to('<shift><alt>w')

    injector.bind_check('editor-active', 'show_offset', 'Tools/Show offset and column#10',
        toggle_offset).to('<ctrl><alt>o')

    injector.bind('editor-with-selection', 'wrap-text', 'Edit/_Wrap block', wrap_text).to('<alt>f')

    injector.bind('editor-with-selection', 'move-selection-left',
        'Edit/Move selection _left', move_word_left).to('<alt>Left')
    injector.bind('editor-with-selection', 'move-selection-right',
        'Edit/Move selection _right', move_word_right).to('<alt>Right')

    injector.bind('editor-with-cursor-in-string', 'swap-quotes',
        'Edit/Swap _quotes', swap_quotes).to('<alt>apostrophe')

    from snaked.core.prefs import add_option
    add_option('DOUBLE_BRACKET_MATCHER', True, "Enable custom bracket matcher")
    add_option('COPY_DELETED_LINE', True, "Put deleted line into clipboard")

    injector.on_ready('editor-with-new-buffer', editor_created)

def editor_created(editor):
    if editor.conf['DOUBLE_BRACKET_MATCHER']:
        from bracket_matcher import attach
        attach(editor)

def in_string(editor):
    from .util import cursor_in_string
    return editor if cursor_in_string(editor.cursor) else None

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

offset_feedbacks = weakref.WeakKeyDictionary()
def get_offset_message(editor):
    cursor = editor.cursor
    return 'offset: %d\ncolumn: %d' % (cursor.get_offset(), cursor.get_line_offset())

def on_buffer_cursor_changed(_buf, _prop, editor_ref):
    editor = editor_ref()
    offset_feedbacks[editor].label.set_text(get_offset_message(editor))

def toggle_offset(editor, is_set):
    if is_set:
        if editor in offset_feedbacks:
            offset_feedbacks[editor].cancel()
        else:
            feedback = offset_feedbacks[editor] = editor.window.floating_manager.add(editor.view,
                TextFeedback(get_offset_message(editor), 'info'), 10)

            editor.window.push_escape(feedback, 10)

            editor_ref = weakref.ref(editor)
            hid = editor.buffer.connect_after('notify::cursor-position', on_buffer_cursor_changed,
                editor_ref)

            def on_cancel(_feedback):
                editor = editor_ref()
                if editor:
                    offset_feedbacks.pop(editor, None)
                    editor.buffer.handler_disconnect(hid)

            feedback.on_cancel(on_cancel)
    else:
        return editor in offset_feedbacks

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

def swap_quotes(editor):
    from .util import source_view_pairs_parser
    start, end = source_view_pairs_parser(editor.cursor)

    buf = editor.buffer
    text = buf.get_text(start, end).decode('utf-8')

    q = text[0]
    if q == '"':
        aq = "'"
    elif q == "'":
        aq = '"'
    else:
        editor.message('Swap quote? What quote?', 'warn')
        return

    if text[-1] == q:
        text = aq + text[1:-1].replace(aq, '\\' + aq).replace('\\' + q, q) + aq
    else:
        editor.message('Swap quote? What quote?', 'warn')
        return

    offset = editor.cursor.get_offset()
    buf.begin_user_action()
    buf.delete(start, end)
    buf.insert_at_cursor(text)
    buf.place_cursor(buf.get_iter_at_offset(offset))
    buf.end_user_action()
