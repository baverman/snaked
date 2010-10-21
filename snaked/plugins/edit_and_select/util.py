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