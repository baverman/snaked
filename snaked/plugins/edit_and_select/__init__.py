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
        end.forward_to_line_end()
        
        return iter.get_text(end).strip() == u''

    def extend_to_block_bounds(self, start, end):
        iter = start.copy()
        ws = self.get_whitespace(iter)
        while True:
            if not iter.backward_lines(1):
                break

            if self.line_is_empty(iter) or self.get_whitespace(iter) != ws:
                break

            start = iter.copy() 

        iter = end.copy()
        iter.backward_lines(1)
        ws = self.get_whitespace(iter)
        while True:
            if not iter.forward_lines(1):
                break
                
            if self.line_is_empty(iter) or self.get_whitespace(iter) != ws:
                break

        end = iter 
            
        return start, end
    
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
    
    def smart_select(self):
        self.select_range(*self.get_smart_select())
