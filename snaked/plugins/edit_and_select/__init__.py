author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Edit and Select'
desc = 'Various edit shortcuts'

import gtk

def init(manager):
    manager.add_shortcut('delete-line', '<ctrl>d', 'Edit', 'Deletes current line', delete_line)
    manager.add_shortcut('smart-select', '<alt>w', 'Selection', 'Smart anything selection', smart_select)
    manager.add_shortcut('show_offset', '<ctrl><alt>o', 'Edit',
        'Show cursor offset and column', show_offset)
    manager.add_shortcut('wrap-text', '<alt>f', 'Edit', 'Wrap text on right margin width', wrap_text)

def delete_line(editor):
    from util import get_line_bounds
    bounds = get_line_bounds(editor.cursor)
    clipboard = editor.view.get_clipboard(gtk.gdk.SELECTION_CLIPBOARD)
    editor.buffer.select_range(*bounds)
    editor.buffer.copy_clipboard(clipboard)

    editor.buffer.begin_user_action()
    editor.buffer.delete(*bounds)
    editor.buffer.end_user_action()

def smart_select(editor):
    from smart_select import get_smart_select
    start, end = get_smart_select(editor)
    editor.buffer.select_range(end, start)

def show_offset(editor):
    editor.message('offset: %d\ncolumn: %d' % (
        editor.cursor.get_offset(), editor.cursor.get_line_offset()), 3000)

def wrap_text(editor):
    buf = editor.buffer
    if not buf.get_has_selection():
        editor.message('Select text block to wrap')
        return

    import textwrap

    start, end = buf.get_selection_bounds()
    start.order(end)
    if end.starts_line():
        end.backward_visible_cursor_position()

    text = buf.get_text(start, end).decode('utf-8')
    text = textwrap.fill(text, width=editor.view.get_right_margin_position())

    buf.begin_user_action()
    buf.place_cursor(end)
    buf.delete(start, end)
    buf.insert_at_cursor(text)
    buf.end_user_action()