class Plugin(object):
    def __init__(self, editor):
        self.editor = editor
        self.buffer = self.editor.buffer
    
    @staticmethod
    def register_shortcuts(manager):
        manager.add('delete-line', '<ctrl>d', 'Edit', 'Deletes current line')
        manager.add('smart-select', '<alt>w', 'Selection', 'Smart anything selection')
        
    def init_shortcuts(self, manager):
        manager.bind(self.editor.activator, 'delete-line', self.delete_line)
        manager.bind(self.editor.activator, 'smart-select', self.smart_select)

    def get_line_bounds(self, cursor=None):
        end = cursor.copy() if cursor else self.editor.cursor
        start = self.buffer.get_iter_at_line(end.get_line())
        
        if not end.ends_line():
            end.forward_to_line_end()
    
        end.forward_char()
        
        return start, end    
    
    def select_range(self, start, end):
        self.buffer.move_mark_by_name('insert', start)
        self.buffer.move_mark_by_name('selection_bound', end)
    
    def delete_line(self):
        self.buffer.begin_user_action()
        self.buffer.delete(*self.get_line_bounds())
        self.buffer.end_user_action()
    
    def cursor_on_start_or_end_whitespace(self, cursor):
        if cursor.starts_line() or cursor.ends_line():
            return True
        
        start, end = self.get_line_bounds(cursor)
        starttext = start.get_text(cursor)
        endtext = cursor.get_text(end)
   
        if starttext.strip() == u'' or endtext.strip() == u'':
            return True
                 
        return False

    def get_whitespace(self, start):
        end = start.copy()
        end.forward_word_end()
        end.backward_word_start()
        return start.get_text(end)
        
    def line_is_empty(self, iter):
        if not iter.starts_line():
            iter = iter.copy()
            iter.set_line(iter.get_line())

        end = iter.copy()
        if not end.ends_line():
            end.forward_to_line_end()
        
        return iter.get_text(end).strip() == u''

    def iter_lines(self, from_iter, delta):
        line_count = from_iter.get_buffer().get_line_count()
        iter = from_iter.copy()
        while True:
            newline = iter.get_line() + delta
            if newline < 0 or newline > line_count - 1:
                return

            iter.set_line(iter.get_line() + delta)
            yield iter

    def get_next_not_empty_line(self, from_iter, delta):
        for iter in self.iter_lines(from_iter, delta):
            if not self.line_is_empty(iter):
                return iter
                
        return None

    def extend_to_block(self, from_iter, delta, ws, skip_empty=False):
        iter = None
        status = None
        for iter in self.iter_lines(from_iter, delta):
            if self.line_is_empty(iter):
                next_non_empty = self.get_next_not_empty_line(iter, delta)
                if next_non_empty:
                    linews = len(self.get_whitespace(next_non_empty))
                    if ( delta > 0 and linews > ws ) or ( skip_empty and linews >= ws):
                        iter.set_line(next_non_empty.get_line())
                    else:
                        status = False
                        break
            
            linews = len(self.get_whitespace(iter))
            if linews < ws:
                status = linews
                break
                
        else:
            if not iter:
                iter = from_iter.copy()
                
            return iter, -1 
        
        iter.set_line(iter.get_line() - delta)
        return iter, status

    def extend_to_block_bounds(self, start, end, skip_empty=False):
        endselect = end.copy()
        endselect.backward_lines(1)

        ws = min(len(self.get_whitespace(start)), len(self.get_whitespace(endselect)))

        newstart, start_status = self.extend_to_block(start, -1, ws)
        newend, end_status = self.extend_to_block(endselect, 1, ws)

        if newstart.equal(start) and newend.equal(endselect):
            if start_status is False:
                newstart, start_status = self.extend_to_block(newstart, -1, ws, True)

            if end_status is False:
                newend, end_status = self.extend_to_block(newend, 1, ws, True)

        if newstart.equal(start) and newend.equal(endselect):
            maxws = max(start_status if start_status is not False else 0,
                end_status if end_status is not False else 0)
                
            if start_status is not False and start_status == maxws:
                newstart.backward_lines(1)

            if end_status is not False and end_status == maxws:
                newend.forward_lines(1)
        
        newend.forward_lines(1)
        return newstart, newend
    
    def smart_extend_selection(self, start, end):
        if start.starts_line() and end.starts_line():
            start, end = self.extend_to_block_bounds(start, end)  
            
        return start, end
    
    def get_smart_select(self):
        if self.buffer.get_has_selection():        
            return self.smart_extend_selection(*self.buffer.get_selection_bounds())
        else:
            cursor = self.editor.cursor
        
            if self.cursor_on_start_or_end_whitespace(cursor):
                return self.get_line_bounds()
                
            return cursor, cursor
    
    def smart_select(self):
        self.select_range(*self.get_smart_select())
