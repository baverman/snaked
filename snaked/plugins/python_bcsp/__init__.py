author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Bad python code save preventer'
desc = 'Prevents from saving of code with syntax errors'

langs = ['python']

import weakref
import time

import glib

last_saves = weakref.WeakKeyDictionary()

def init(manager):
    manager.add_global_option('PYTHON_BCSP_GOTO_TO_ERROR', True,
        'Automatically jumps to line where syntax error occured')

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
        ast.parse(editor.utext.encode(editor.encoding), editor.uri)
    except SyntaxError, e:
        message = '%s at line <b>%d</b>' % (glib.markup_escape_text(e.msg), e.lineno)
        if e.text:
            message += '\n\n' + glib.markup_escape_text(e.text)

        editor.message(message, 10000, markup=True)

        if editor.snaked_conf['PYTHON_BCSP_GOTO_TO_ERROR']:
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