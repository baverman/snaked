author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Python flakes'
desc = 'Basic python linter'
langs = ['python']

import os.path
from snaked.core.problems import mark_problems, attach_to_editor

def init(manager):
    manager.add_global_option('PYFLAKES_RUN_ON_FILE_LOAD', True, 'Run pyflakes check on file load')

def editor_opened(editor):
    editor.connect('file-saved', on_file_saved)
    attach_to_editor(editor)
    if editor.snaked_conf['PYFLAKES_RUN_ON_FILE_LOAD'] \
            and editor.uri and os.path.exists(editor.uri):
        add_job(editor)

def on_file_saved(editor):
    add_job(editor)

def get_problem_list(filename):
    import subprocess
    import re

    stdout, stderr = subprocess.Popen(['/usr/bin/env', 'pyflakes', filename],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

    if stderr:
        raise Exception('python_flakes plugin: ' + stderr)

    result = []
    match_name = re.compile(r"'(.*?)'")
    for m in re.finditer(r"(?m)^.*?:(?P<line>\d+):\s*(?P<message>.*$)", stdout):
        line, message = m.group('line', 'message')
        name = match_name.search(message)
        if not name:
            raise Exception("Can't parse variable name in " + message)

        result.append((int(line), name.group(1), message))

    return result

def add_job(editor):
    from threading import Thread
    from snaked.util import idle

    def job():
        try:
            problems = get_problem_list(editor.uri)
        except Exception, e:
            idle(editor.message, str(e), 5000)
            return

        idle(mark_problems, editor, 'flakes', problems)

    Thread(target=job).start()
