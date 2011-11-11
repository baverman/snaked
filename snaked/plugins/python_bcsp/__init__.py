author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Bad python code save preventer'
desc = 'Prevents from saving of code with syntax errors'

import weakref
import time

import glib

last_feedbacks = weakref.WeakKeyDictionary()

def init(injector):
    injector.on_ready('editor-with-new-buffer', editor_created)

    from snaked.core.prefs import add_option
    add_option('PYTHON_BCSP_GOTO_TO_ERROR', True,
        'Automatically jumps to line where syntax error occured')

def editor_created(editor):
    editor.connect('before-file-save', on_editor_before_file_save)

def last_save_occurred_in(fb, seconds):
    return fb and time.time() - fb.start < seconds

def process_error(editor, fb, newfb):
    last_feedbacks[editor] = newfb
    if last_save_occurred_in(fb, 0.5):
        return False
    else:
        editor.before_file_save.stop_emission()
        return True

def on_editor_before_file_save(editor):
    from snaked.plugins.python import handlers
    try:
        h = handlers[editor]
    except KeyError:
        return False

    last_fb = last_feedbacks.pop(editor, None)
    if last_fb:
        last_fb.cancel()

    error = h.env.check_syntax(editor.utext)
    if error:
        location, msg = error
        if location[0] == 'end-of-file':
            lineno = editor.buffer.get_line_count()
        else:
            lineno = location[1]

        message = '%s at line <b>%d</b>' % (glib.markup_escape_text(msg), lineno)

        new_fb = editor.message(message, 'error', 10000, markup=True)

        if editor.conf['PYTHON_BCSP_GOTO_TO_ERROR']:
            if editor.cursor.get_line() != lineno - 1:
                editor.add_spot()
                if location[0] == 'line-offset':
                    it = editor.buffer.get_iter_at_line_offset(lineno-1, location[2])
                elif location[0] == 'end-of-line':
                    it = editor.buffer.get_iter_at_line(location[1] - 1)
                    if not it.ends_line():
                        it.forward_to_line_end()
                elif location[0] == 'end-of-file':
                    it = editor.buffer.get_bounds()[1]
                else:
                    it = editor.cursor

                editor.buffer.place_cursor(it)
                editor.scroll_to_cursor()

        return process_error(editor, last_fb, new_fb)

    if last_save_occurred_in(last_fb, 10):
        editor.message('Good job!', 'done')