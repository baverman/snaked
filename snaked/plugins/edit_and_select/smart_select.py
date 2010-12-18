from util import (iter_lines, line_is_empty, get_next_not_empty_line, get_whitespace,
    line_text, next_line, prev_line, cursor_on_start_or_end_whitespace, get_line_bounds)

def extend_with_gap(from_iter, ws, delta):
    n = None
    for p, n in iter_lines(from_iter, delta):
        if line_is_empty(n):
            ne = get_next_not_empty_line(n, delta)
            if ne and len(get_whitespace(ne)) >= ws:
                n.set_line(ne.get_line())
            else:
                return p

        n_ws = len(get_whitespace(n))
        if n_ws < ws:
            return p

    return n if n else from_iter.copy()

def extend_without_gap(from_iter, ws, delta):
    n = None
    for p, n in iter_lines(from_iter, delta):
        if line_is_empty(n):
            ne = get_next_not_empty_line(n, delta)
            if ne and delta > 0 and len(get_whitespace(ne)) > ws:
                n.set_line(ne.get_line())
            else:
                return p

        n_ws = len(get_whitespace(n))
        if n_ws < ws:
            return p

    return n if n else from_iter.copy()

def extend_block_without_gap(from_iter, ws, delta):
    n = None
    for p, n in iter_lines(from_iter, delta):
        if line_is_empty(n):
            ne = get_next_not_empty_line(n, delta)
            if ne:
                n.set_line(ne.get_line())
            else:
                return p

        n_ws = len(get_whitespace(n))

        if n_ws < ws or ( n_ws == ws and len(line_text(n).strip()) > 4 ):
            return p

    return n if n else from_iter.copy()

def block_smart_extend(has_selection, start, end):
    end = end.copy()
    if not end.is_end():
        end.backward_lines(1)

    start_ws = len(get_whitespace(start))
    prev_empty = start.is_start() or line_is_empty(prev_line(start))
    prev_ws = len(get_whitespace(prev_line(start)))

    end_ws = len(get_whitespace(end))
    next_empty = end.is_end() or line_is_empty(next_line(end))
    next_ws = len(get_whitespace(next_line(end)))

    newstart, newend = start.copy(), end

    if not has_selection and start.get_line() == end.get_line() and \
            ( next_empty or next_ws < end_ws ) and (prev_empty or prev_ws < start_ws):
        pass
    elif not prev_empty and not next_empty and prev_ws == start_ws == next_ws == end_ws:
        newstart = extend_without_gap(start, start_ws, -1)
        newend = extend_without_gap(end, end_ws, 1)
    elif prev_empty and not next_empty and next_ws == end_ws:
        newend = extend_without_gap(end, end_ws, 1)
    elif not prev_empty and next_empty and prev_ws == start_ws:
        newstart = extend_without_gap(start, start_ws, -1)
    elif not next_empty and next_ws > start_ws:
        newend = extend_block_without_gap(end, start_ws, 1)
    elif ( not next_empty and next_ws == start_ws ) or ( not prev_empty and prev_ws >= start_ws ):
        if not prev_empty:
            newstart = extend_without_gap(start, start_ws, -1)
        if not next_empty:
            newend = extend_without_gap(end, start_ws, 1)
    elif next_empty and prev_empty:
        newstart = extend_with_gap(start, start_ws, -1)
        newend = extend_with_gap(end, start_ws, 1)
    elif next_empty and not prev_empty and prev_ws < start_ws:
        newend = extend_with_gap(end, start_ws, 1)

    if has_selection and start.equal(newstart) and end.equal(newend):
        if not prev_empty:
            newstart.backward_lines(1)
        else:
            ne = get_next_not_empty_line(start, -1)
            if ne:
                newstart = ne

        if not next_empty and len(line_text(next_line(end)).strip()) < 5:
            newend.forward_lines(1)

    newend.forward_lines(1)
    return newstart, newend

def get_smart_select(editor):
    if editor.buffer.get_has_selection():
        start, end = editor.buffer.get_selection_bounds()
        if start.starts_line() and ( end.starts_line() or end.is_end() ):
            return block_smart_extend(True, start, end)
        else:
            return line_smart_extend(True, start, end)
    else:
        cursor = editor.cursor

        if cursor_on_start_or_end_whitespace(cursor):
            return block_smart_extend(False, *get_line_bounds(cursor))
        else:
            return line_smart_extend(False, cursor, cursor.copy())

def get_words_bounds(cursor, include_hyphen=False):
    return backward_word_start(cursor, include_hyphen), forward_word_end(cursor, include_hyphen)

def char_is_word(char, include_hyphen=False):
    return char and char.isalnum() or char == u'_' or (include_hyphen and char == u'-')

def backward_word_start(iter, include_hyphen=False):
    iter = iter.copy()
    iter.backward_char()
    while char_is_word(iter.get_char(), include_hyphen):
        iter.backward_char()

    iter.forward_char()

    return iter

def forward_word_end(iter, include_hyphen=False):
    iter = iter.copy()
    while char_is_word(iter.get_char()):
        iter.forward_char()

    return iter

def line_smart_extend(has_selection, start, end):
    from snaked.util import pairs_parser

    def ahtung():
        start.set_line(start.get_line())
        if not end.starts_line():
            end.set_line(end.get_line() + 1)

        return start, end

    left = start.copy()
    left.backward_chars(3)
    lchars = left.get_text(start).decode('utf-8')

    right = end.copy()
    right.forward_chars(3)
    rchars = end.get_text(right).decode('utf-8')

    if not rchars:
        rchars = [None]

    if not lchars:
        lchars = [None]

    text = start.get_buffer().get_text(*start.get_buffer().get_bounds()).decode('utf8')
    br, spos, epos = pairs_parser.get_brackets(text, start.get_offset())
    in_quotes = br in ('"', "'", '"""', "'''")
    #print br, spos, epos, start.get_offset()

    if not in_quotes and rchars[0] in (u'(', u'[', "'", '"'):
        try:
            br, spos, epos = pairs_parser.get_brackets(text, end.get_offset() + 1)
            #print br, spos, epos, end.get_offset() + 1
        except TypeError:
            br = None

        if not br: return ahtung()

        end.set_offset(epos)
    elif char_is_word(lchars[-1]) or char_is_word(rchars[0]):
        start = backward_word_start(start, in_quotes)
        end = forward_word_end(end, in_quotes)
    elif lchars[-1] == u'.' or rchars[0] == u'.':
        if lchars[-1] == u'.':
            start.backward_char()
            start = backward_word_start(start)
        if rchars[0] == u'.':
            end.forward_char()
            end = forward_word_end(end)
    else:
        if not br: return ahtung()

        ostart = start.copy()
        oend = end.copy()

        start.set_offset(spos)
        end.set_offset(epos - 1)

        if ostart.equal(start) and oend.equal(end):
            start.backward_chars(len(br))
            end.forward_chars(len(br))

    return start, end
