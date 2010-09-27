class Plugin(object):
    def __init__(self, editor):
        self.editor = editor
    
    @staticmethod
    def register_shortcuts(manager):
        manager.add('delete-line', '<ctrl>d', 'Edit', 'Deletes current line')
        manager.add('smart-select', '<alt>w', 'Selection', 'Smart word, quotes, block selection')
        
    def init_shortcuts(self, manager):
        manager.bind(self.editor.activator, 'delete-line', self.delete_line)
        manager.bind(self.editor.activator, 'smart-select', self.smart_select)

    def delete_line(self):
        buffer = self.editor.buffer
        
        end = self.editor.cursor
        start = buffer.get_iter_at_line(end.get_line())
        
        if not end.ends_line():
            end.forward_to_line_end()
    
        end.forward_char()    
        
        buffer.begin_user_action()
        buffer.delete(start, end)
        buffer.end_user_action()
        
    def smart_select(self):
        pass