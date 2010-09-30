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
    buffer.move_mark_by_name('insert', start)
    buffer.move_mark_by_name('selection_bound', end)
    
def cursor_on_start_or_end_whitespace(cursor):
    if cursor.starts_line() or cursor.ends_line():
        return True
    
    start, end = get_line_bounds(cursor)
    starttext = start.get_text(cursor)
    endtext = cursor.get_text(end)

    if starttext.strip() == u'' or endtext.strip() == u'':
        return True
             
    return False

def get_whitespace(start):
    end = start.copy()
    end.forward_word_end()
    end.backward_word_start()
    return start.get_text(end)
        
def line_is_empty(iter):
    if not iter.starts_line():
        iter = iter.copy()
        iter.set_line(iter.get_line())

    end = iter.copy()
    if not end.ends_line():
        end.forward_to_line_end()
    
    return iter.get_text(end).strip() == u''

def iter_lines(from_iter, delta):
    line_count = from_iter.get_buffer().get_line_count()
    iter = from_iter.copy()
    while True:
        newline = iter.get_line() + delta
        if newline < 0 or newline > line_count - 1:
            return

        iter.set_line(iter.get_line() + delta)
        yield iter

def get_next_not_empty_line(from_iter, delta):
    for iter in iter_lines(from_iter, delta):
        if not line_is_empty(iter):
            return iter
            
    return None

def extend_to_block(from_iter, delta, ws, skip_empty=False):
    iter = None
    status = None
    for iter in iter_lines(from_iter, delta):
        if line_is_empty(iter):
            next_non_empty = get_next_not_empty_line(iter, delta)
            if next_non_empty:
                linews = len(get_whitespace(next_non_empty))
                if ( delta > 0 and linews > ws ) or ( skip_empty and linews >= ws):
                    iter.set_line(next_non_empty.get_line())
                else:
                    status = False
                    break
        
        linews = len(get_whitespace(iter))
        if linews < ws:
            status = linews
            break
            
    else:
        if not iter:
            iter = from_iter.copy()
            
        return iter, -1 
    
    iter.set_line(iter.get_line() - delta)
    return iter, status

def extend_to_block_bounds(start, end, skip_empty=False):
    endselect = end.copy()
    endselect.backward_lines(1)

    ws = min(len(get_whitespace(start)), len(get_whitespace(endselect)))

    newstart, start_status = extend_to_block(start, -1, ws)
    newend, end_status = extend_to_block(endselect, 1, ws)

    if newstart.equal(start) and newend.equal(endselect):
        if start_status is False:
            newstart, start_status = extend_to_block(newstart, -1, ws, True)

        if end_status is False:
            newend, end_status = extend_to_block(newend, 1, ws, True)

    if newstart.equal(start) and newend.equal(endselect):
        maxws = max(start_status if start_status is not False else 0,
            end_status if end_status is not False else 0)
            
        if start_status is not False and start_status == maxws:
            newstart.backward_lines(1)

        if end_status is not False and end_status == maxws:
            newend.forward_lines(1)
    
    newend.forward_lines(1)
    return newstart, newend
    
def smart_extend_selection(start, end):
    if start.starts_line() and end.starts_line():
        start, end = extend_to_block_bounds(start, end)  
        
    return start, end
    
def get_smart_select(editor):
    if editor.buffer.get_has_selection():        
        return smart_extend_selection(*editor.buffer.get_selection_bounds())
    else:
        cursor = editor.cursor
    
        if cursor_on_start_or_end_whitespace(cursor):
            return smart_extend_selection(*get_line_bounds(cursor))
            
        return cursor, cursor
    
def smart_select(editor):
    select_range(editor.buffer, *get_smart_select(editor))
