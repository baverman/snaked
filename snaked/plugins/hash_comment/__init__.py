author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Hash comment'
desc = '(Un)Comments line or selection with hashes'

import gtk
import re

langs = ['python', 'sh', 'ruby', 'perl']

def init(manager):
    manager.add_shortcut('comment-code', '<ctrl>slash', 'Edit',
        'Comments/uncomments current line or selection', comment)

#Action
def comment(editor):
    r = get_bounds(editor)
    traversor = make_line_traversor(editor.buffer, r)

    if all(line_is_hashed(l) for l in traversor()):
        uncomment_range(editor, traversor)
    else:
        comment_range(editor, traversor)

def make_line_traversor(buffer, r):
    start, end = r
    start, stop = start.get_line(), end.get_line() + 1
    def inner():
        for i in xrange(start, stop):
            yield buffer.get_iter_at_line(i)

    return inner

def get_bounds(editor):
    if editor.buffer.get_has_selection():
        start, end = editor.buffer.get_selection_bounds()
        if start.ends_line():
            start.set_line(start.get_line() + 1)

        if end.starts_line():
            end.set_line(end.get_line() - 1)

        return start, end
    else:
        cursor = editor.cursor
        return cursor, cursor.copy()

def line_is_hashed(iter):
    text = get_line_text(iter).strip()
    return not text or text[0] == u'#'

def get_line_text(iter):
    if not iter.starts_line():
        iter = iter.copy()
        iter.set_line(iter.get_line())

    end = iter.copy()
    if not end.ends_line():
        end.forward_to_line_end()

    return iter.get_text(end)

def line_is_empty(iter):
    return get_line_text(iter).strip() == u''

def comment_range(editor, traversor):
    ws_match = re.compile(r'[ \t]*')
    min_indent = 1000
    min_indent_text = ''
    for iter in traversor():
        if not line_is_empty(iter):
            match = ws_match.match(get_line_text(iter))
            if match and len(match.group()) < min_indent:
                min_indent = len(match.group())
                min_indent_text = match.group()

    if min_indent == 1000:
        min_indent = 0

    editor.buffer.begin_user_action()
    for iter in traversor():
        if line_is_empty(iter):
            line_end = iter.copy()
            line_end.forward_to_line_end()
            if iter.get_line() == line_end.get_line():
                editor.buffer.delete(iter, line_end)
            editor.buffer.insert(iter, min_indent_text)
        else:
            iter.forward_chars(min_indent)

        editor.buffer.insert(iter, u'#')

    editor.buffer.end_user_action()

def uncomment_range(editor, traversor):
    editor.buffer.begin_user_action()
    for iter in traversor():
        if not line_is_empty(iter):
            if get_line_text(iter).strip() == '#':
                line_end = iter.copy()
                line_end.forward_to_line_end()
                editor.buffer.delete(iter, line_end)
            else:
                editor.buffer.delete(*iter.forward_search(u'#', gtk.TEXT_SEARCH_VISIBLE_ONLY))

    editor.buffer.end_user_action()
