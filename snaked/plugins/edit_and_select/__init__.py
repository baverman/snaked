import re

def init(manager):
    manager.add_shortcut('delete-line', '<ctrl>d', 'Edit', 'Deletes current line', delete_line)
    manager.add_shortcut('smart-select', '<alt>w', 'Selection', 'Smart anything selection', smart_select)

# Delete line handler
def delete_line(editor):
    editor.buffer.begin_user_action()
    editor.buffer.delete(*get_line_bounds(editor.cursor))
    editor.buffer.end_user_action()

def get_line_bounds(cursor):
    end = cursor.copy()
    start = end.copy()
    start.set_line(end.get_line())
    
    if not end.ends_line():
        end.forward_to_line_end()

    end.forward_char()
    
    return start, end    
    
def select_range(buffer, start, end):
    buffer.select_range(end, start)
    
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
    return line_text(iter).strip() == u''

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

def extend_with_gap(from_iter, ws, delta):
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
    
    return n

def extend_without_gap(from_iter, ws, delta):
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
    
    return n

def extend_block_without_gap(from_iter, ws, delta):
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
    
    return n

def block_smart_extend(has_selection, start, end):
    end = end.copy()
    end.backward_lines(1)
    
    start_ws = len(get_whitespace(start))
    prev_empty = line_is_empty(prev_line(start))
    prev_ws = len(get_whitespace(prev_line(start)))
    
    end_ws = len(get_whitespace(end))
    next_empty = line_is_empty(next_line(end))
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
    
def smart_extend_selection(has_selection, start, end):
    if start.starts_line() and end.starts_line():
        start, end = block_smart_extend(has_selection, start, end)  
        
    return start, end
    
def get_smart_select(editor):
    if editor.buffer.get_has_selection():        
        return smart_extend_selection(True, *editor.buffer.get_selection_bounds())
    else:
        cursor = editor.cursor
    
        if cursor_on_start_or_end_whitespace(cursor):
            return smart_extend_selection(False, *get_line_bounds(cursor))
            
        return cursor, cursor
    
def smart_select(editor):
    select_range(editor.buffer, *get_smart_select(editor))
