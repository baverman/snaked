author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Edit and Select'
desc = 'Various edit shortcuts'

def init(manager):
    manager.add_shortcut('delete-line', '<ctrl>d', 'Edit', 'Deletes current line', delete_line)
    manager.add_shortcut('smart-select', '<alt>w', 'Selection', 'Smart anything selection', smart_select)

def delete_line(editor):
    from util import get_line_bounds
    editor.buffer.begin_user_action()
    editor.buffer.delete(*get_line_bounds(editor.cursor))
    editor.buffer.end_user_action()

def smart_select(editor):
    from util import select_range
    from smart_select import get_smart_select
    select_range(editor.buffer, *get_smart_select(editor))