class Plugin(object):
    def __init__(self, editor):
        self.editor = editor
    
    @staticmethod
    def register_shortcuts(manager):
        manager.add('delete-line', '<ctrl>d', 'Edit', 'Deletes current line')
        manager.add('smart-select', '<alt>w', 'Selection', 'Smart anything selection')
        
    def init_shortcuts(self, manager):
        manager.bind(self.editor.activator, 'delete-line', self.delete_line)
        manager.bind(self.editor.activator, 'smart-select', self.smart_select)

    def get_line_bounds(self, cursor=None):
        end = cursor.copy() if cursor else self.editor.cursor
        start = self.editor.buffer.get_iter_at_line(end.get_line())
        
        if not end.ends_line():
            end.forward_to_line_end()
    
        end.forward_char()
        
        return start, end    
    
    def select_range(self, start, end):
        self.editor.buffer.move_mark_by_name('insert', start)
        self.editor.buffer.move_mark_by_name('selection_bound', end)
    
    def delete_line(self):
        buffer = self.editor.buffer
        
        buffer.begin_user_action()
        buffer.delete(*self.get_line_bounds())
        buffer.end_user_action()
    
    def cursor_on_start_or_end_whitespace(self, cursor):
        if cursor.starts_line() or cursor.ends_line():
            return True
        
        start, end = self.get_line_bounds(cursor)
        starttext = start.get_text(cursor)
        endtext = cursor.get_text(end)
   
        if starttext.strip() == u'' or endtext.strip() == u'':
            return True
                 
        return False
        
    def smart_select(self):
        cursor = self.editor.cursor

        if self.cursor_on_start_or_end_whitespace(cursor):
            self.select_range(*self.get_line_bounds())
            return
            
        
                