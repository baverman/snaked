import re

def get_line_bounds(cursor):
    end = cursor.copy()
    start = end.copy()
    start.set_line(end.get_line())

    very_end = end.copy()
    very_end.forward_to_end()

    if end.get_line() == very_end.get_line():
        start.backward_char()
        return start, very_end

    if not end.ends_line():
        end.forward_to_line_end()

    end.forward_char()

    return start, end

def cursor_on_start_or_end_whitespace(cursor):
    if cursor.starts_line() or cursor.ends_line():
        return True

    start, end = get_line_bounds(cursor)
    starttext = start.get_text(cursor)
    endtext = cursor.get_text(end)

    if starttext.strip() == u'' or endtext.strip() == u'':
        return True

    return False

match_ws = re.compile(u'(?u)^[ \t]*')
def get_whitespace(start):
    if start.is_end():
        return u''

    match = match_ws.search(line_text(start))
    if match:
        return match.group(0)
    else:
        return u''

def line_text(iter):
    if not iter.starts_line():
        iter = iter.copy()
        iter.set_line(iter.get_line())

    end = iter.copy()
    if not end.ends_line():
        end.forward_to_line_end()

    return iter.get_text(end)

def line_is_empty(iter):
    return iter.is_end() or line_text(iter).strip() == u''

def iter_lines(from_iter, delta):
    line_count = from_iter.get_buffer().get_line_count()
    iter = from_iter.copy()
    while True:
        newline = iter.get_line() + delta
        if newline < 0 or newline > line_count - 1:
            return

        olditer = iter.copy()
        iter.set_line(iter.get_line() + delta)

        yield olditer, iter

def get_next_not_empty_line(from_iter, delta):
    for p, n in iter_lines(from_iter, delta):
        if not line_is_empty(n):
            return n

    return None

def next_line(iter):
    result = iter.copy()
    result.set_line(result.get_line() + 1)
    return result

def prev_line(iter):
    result = iter.copy()
    result.set_line(result.get_line() - 1)
    return result

def cursor_in_string(cursor):
    buf = cursor.get_buffer()
    if buf.iter_has_context_class(cursor, 'string'):
        cursor = cursor.copy()
        if cursor.backward_char():
            if buf.iter_has_context_class(cursor, 'string'):
                return True

    return False

def find_closest_bracket(cursor, brackets, forward=True):
    buf = cursor.get_buffer()

    iters = []
    for br in brackets:
        it = cursor
        while True:
            if forward:
                result = it.forward_search(br, 0)
            else:
                result = it.backward_search(br, 0)

            if not result:
                break

            if buf.iter_has_context_class(result[0], 'string'):
                it = result[forward]
            else:
                break

        if result:
            iters.append((br, result[forward]))

    if not iters:
        return None, None

    return (max, min)[forward](iters, key=lambda r:r[1].get_offset())

brackets = {
    '(': ')',
    '{': '}',
    '[': ']',
    ')': '(',
    '}': '{',
    ']': '[',
}

def find_bracket(from_iter, br, obr, dir):
    buf = from_iter.get_buffer()
    iter = from_iter.copy()
    if dir < 0:
        iter.forward_cursor_positions(dir)
    depth = 1
    while True:
        if not iter.forward_cursor_positions(dir):
            break

        if buf.iter_has_context_class(iter, 'string'):
            continue

        c = iter.get_char()
        if c == br:
            depth -= 1
        elif c == obr:
            depth += 1

        if depth == 0:
            if dir > 0:
                iter.forward_cursor_positions(dir)
            return iter

    return None

def get_text(start, slice):
    start = start.copy()
    end = start.copy()
    end.forward_chars(slice)
    start.order(end)
    return start.get_text(end)

def source_view_pairs_parser(cursor):
    buf = cursor.get_buffer()

    if cursor_in_string(cursor):
        start = cursor.copy()
        buf.iter_backward_to_context_class_toggle(start, 'string')
        end = cursor.copy()
        buf.iter_forward_to_context_class_toggle(end, 'string')

        return start, end

    br, start = find_closest_bracket(cursor, ('(', '[', '{'), False)
    if not start: return None, None
    obr = brackets[br]

    _, end = find_closest_bracket(start, (obr,), True)
    if not end: return None, None

    if cursor.in_range(start, end):
        end = find_bracket(start, obr, br, 1)
    else:
        br, end = find_closest_bracket(cursor, (')', ']', '}'), True)
        if not end: return None, None
        obr = brackets[br]

        _, start = find_closest_bracket(end, (obr,), False)
        if not start: return None, None

        if cursor.in_range(start, end):
            start = find_bracket(end, obr, br, -1)
        else:
            return None, None

    if start and end:
        return start, end
    else:
        return None, None
