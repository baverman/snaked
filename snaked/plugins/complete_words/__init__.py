author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Complete words'
desc = 'Cycle through possible word completions'

from gobject import timeout_add
from string import whitespace
from uxie.utils import refresh_gui, connect, idle

buffers_to_update = []

def init(injector):
    injector.bind('editor-active', 'complete-word', 'Edit/Complete _word#80', cycle).to('<alt>slash')

    timeout_add(3000, update_words_timer)
    injector.on_ready('buffer-loaded', buffer_loaded)

def buffer_loaded(buf):
    buf.complete_words_on_changed_handler_id = connect(buf, 'changed', on_buffer_changed, True, True)
    idle(add_update_job, buf)

def add_update_job(buf):
    import words
    words.add_job(buf.uri, buf.get_text(*buf.get_bounds()))

def update_words_timer():
    if buffers_to_update:
        for buf in buffers_to_update:
            add_update_job(buf)

        buffers_to_update[:] = []

    return True

def on_buffer_changed(buf, *args):
    buf.complete_words_changed = True
    if not buf in buffers_to_update:
        buffers_to_update.append(buf)

def is_valid_character(c):
    if c in whitespace:
        return False

    return c.isalpha() or c.isdigit() or (c in ("-", "_"))

def backward_to_word_begin(iterator):
    if iterator.starts_line(): return iterator
    iterator.backward_char()
    while is_valid_character(iterator.get_char()):
        iterator.backward_char()
        if iterator.starts_line(): return iterator
    iterator.forward_char()
    return iterator

def forward_to_word_end(iterator):
    if iterator.ends_line(): return iterator
    if not is_valid_character(iterator.get_char()): return iterator
    while is_valid_character(iterator.get_char()):
        iterator.forward_char()
        if iterator.ends_line(): return iterator
    return iterator

def get_word_before_cursor(buf, iterator):
    # If the cursor is in front of a valid character we ignore
    # word completion.
    if is_valid_character(iterator.get_char()):
        return None, None

    if iterator.starts_line():
        return None, None

    iterator.backward_char()

    if not is_valid_character(iterator.get_char()):
        return None, None

    start = backward_to_word_begin(iterator.copy())
    end = forward_to_word_end(iterator.copy())
    word = buf.get_text(start, end).strip()

    return word, start

def get_matches(string):
    import words

    if not words.words:
        return None

    result = []
    for word, files in words.words.iteritems():
        if word != string and word.startswith(string):
            result.append((word, sum(files.values())))

    result.sort(key=lambda r: r[1], reverse=True)

    return [r[0] for r in result]

def cycle(editor):
    buf, it = editor.buffer, editor.cursor
    word_to_complete, start = get_word_before_cursor(buf, it)

    if not word_to_complete:
        return False

    if getattr(buf, 'complete_words_changed', False):
        editor.complete_words_data = None, None
        buf.complete_words_changed = False

    try:
        start_word, start_offset = editor.complete_words_data
    except AttributeError:
        start_word, start_offset = editor.complete_words_data = None, None

    if not start_word or start_offset != start.get_offset():
        start_word = word_to_complete
        start_offset = start.get_offset()
        editor.complete_words_data = start_word, start_offset

    matches = get_matches(start_word)
    if matches:
        idx = 0
        try:
            idx = matches.index(word_to_complete)
            idx = (idx + 1) % len(matches)
        except ValueError:
            pass

        if matches[idx] == word_to_complete:
            editor.message("Word completed already")
            return False

        buf.handler_block(buf.complete_words_on_changed_handler_id)

        end = editor.cursor
        buf.delete(start, end)
        buf.insert(start, matches[idx])

        refresh_gui()
        buf.handler_unblock(buf.complete_words_on_changed_handler_id)
    else:
        editor.message("No word to complete")
