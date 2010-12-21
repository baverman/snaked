author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Bad python code save preventer'
desc = 'Prevents from saving of code with syntax errors'

langs = ['python']

import weakref
import time

last_saves = weakref.WeakKeyDictionary()

def editor_created(editor):
    editor.connect('before-file-save', on_editor_before_file_save)

def add_last_save(editor):
    last_saves[editor] = time.time()

def last_save_occurred_in(editor, seconds):
    return editor in last_saves and time.time() - last_saves[editor] < seconds

def process_error(editor):
    if last_save_occurred_in(editor, 0.5):
        return False
    else:
        add_last_save(editor)
        editor.before_file_save.stop_emission()
        return True

def on_editor_before_file_save(editor):
    import ast
    try:
        ast.parse(editor.utext, editor.uri)
    except SyntaxError, e:
        editor.message(str(e) + '\n\n' + e.text, 10000)

        if editor.cursor.get_line() != e.lineno - 1:
            editor.add_spot()
            editor.goto_line(e.lineno)

        return process_error(editor)
    except Exception, e:
        editor.message(str(e), 10000)
        return process_error(editor)

    if last_save_occurred_in(editor, 10):
        editor.message('Good job!')

    try:
        del last_saves[editor]
    except KeyError:
        pass