author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Complete words'
desc = 'Cycle through possible word completions'

import weakref

from gobject import timeout_add, source_remove
from string import whitespace

from snaked.util import idle, refresh_gui
from snaked.signals import connect_all, connect_external

editors_to_update = []
timer_source_id = None
handlers = weakref.WeakKeyDictionary()

def init(manager):
    manager.add_shortcut('complete-word', '<alt>slash', 'Edit',
        'Cycle through word completions', complete_word)
    
    global timer_source_id
    timer_source_id = timeout_add(3000, update_words_timer)

def complete_word(editor):
    try:
        h = handlers[editor]
    except KeyError:
        return
        
    h.cycle()

def editor_opened(editor):
    idle(add_update_job, editor)
    h = Plugin(editor)
    handlers[editor] = h

def editor_closed(editor):
    try:
        del handlers[editor]
    except KeyError:
        pass
            
def quit():
    source_remove(timer_source_id)

def add_update_job(editor):
    import words
    words.add_job(editor.uri, editor.text)

def update_words_timer():
    if editors_to_update:
        for e in editors_to_update:
            add_update_job(e)
        
        editors_to_update[:] = []
    
    return True


class Plugin(object):
    def __init__(self, editor):
        self.editor = editor
        connect_all(self, buffer=editor.buffer)
        self.start_word = None
        self.start_offset = None
    
    @connect_external('buffer', 'changed', idle=True)    
    def on_buffer_changed(self, *args):
        if not self.editor in editors_to_update:
            editors_to_update.append(self.editor)
            
        self.start_word = None
        self.start_iter = None

    def is_valid_character(self, c):
        if c in whitespace:
            return False
        
        return c.isalpha() or c.isdigit() or (c in ("-", "_"))

    def backward_to_word_begin(self, iterator):
        if iterator.starts_line(): return iterator
        iterator.backward_char()
        while self.is_valid_character(iterator.get_char()):
            iterator.backward_char()
            if iterator.starts_line(): return iterator
        iterator.forward_char()
        return iterator

    def forward_to_word_end(self, iterator):
        if iterator.ends_line(): return iterator
        if not self.is_valid_character(iterator.get_char()): return iterator
        while self.is_valid_character(iterator.get_char()):
            iterator.forward_char()
            if iterator.ends_line(): return iterator
        return iterator
    
    def get_word_before_cursor(self):
        iterator = self.editor.cursor
        # If the cursor is in front of a valid character we ignore
        # word completion.
        if self.is_valid_character(iterator.get_char()):
            return None, None
        
        if iterator.starts_line():
            return None, None
    
        iterator.backward_char()
        
        if not self.is_valid_character(iterator.get_char()):
            return None, None
    
        start = self.backward_to_word_begin(iterator.copy())
        end = self.forward_to_word_end(iterator.copy())
        word = self.editor.buffer.get_text(start, end).strip()
        
        return word, start

    def get_matches(self, string):
        import words
        
        if not words.words:
            return None
        
        result = []
        for word, files in words.words.iteritems():
            if word != string and word.startswith(string):
                result.append((word, sum(files.values())))
                
        result.sort(key=lambda r: r[1], reverse=True)
        
        return [r[0] for r in result]

    def cycle(self):
        word_to_complete, start = self.get_word_before_cursor()
        
        if not word_to_complete:
            return False

        if not self.start_word or self.start_offset != start.get_offset():
            self.start_word = word_to_complete
            self.start_offset = start.get_offset()

        matches = self.get_matches(self.start_word)
        if matches:
            idx = 0
            try:
                idx = matches.index(word_to_complete)
                idx = (idx + 1) % len(matches)
            except ValueError:
                pass

            if matches[idx] == word_to_complete:
                self.editor.message("Word completed already")
                return False
                
            self.on_buffer_changed_handler.block()             
            
            end = self.editor.cursor
            self.editor.buffer.delete(start, end)
            self.editor.buffer.insert(start, matches[idx])
            
            refresh_gui()
            self.on_buffer_changed_handler.unblock()             
        else:
            self.editor.message("No word to complete")
