author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Edit and Select'
desc = 'Various edit shortcuts'

import gtk

def init(manager):
    manager.add_shortcut('delete-line', '<ctrl>d', 'Edit', 'Deletes current line', delete_line)
    manager.add_shortcut('smart-select', '<alt>w', 'Selection', 'Smart anything selection', smart_select)
    manager.add_shortcut('show_offset', '<ctrl><alt>o', 'Edit', 'Show cursor offset', show_offset)

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
    from util import select_range
    from smart_select import get_smart_select
    select_range(editor.buffer, *get_smart_select(editor))
    
def show_offset(editor):
    editor.message(str(editor.cursor.get_offset()), 3000)
