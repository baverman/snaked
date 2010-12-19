author = 'Anton Bobrov<bobrov@vl.ru>/Fabien Devaux<fdev31@gmail.com>'
name = 'Pylint'
desc = 'Advanced python linter'
langs = ['python']


import os.path
import re

from snaked.core.problems import mark_problems, attach_to_editor, clear_problems

def init(manager):
    manager.add_global_option('PYLINT_CHECK_ON_SAVE', False, 'Run pylint on every file save')
    manager.add_global_option('PYLINT_CMD', 'pylint -f parseable -r n -i y',
        'Command to run pylint')
    manager.add_shortcut('python-run-pylint', 'F4', 'Python', 'Run pylint', add_job)
    manager.add_shortcut('python-clear-pylint-warns', '<shift>F4', 'Python',
        'Clear pylint warnings', clear_pylint_warns)

def editor_opened(editor):
    attach_to_editor(editor)

    if editor.snaked_conf['PYLINT_CHECK_ON_SAVE']:
        editor.connect('file-saved', on_file_saved)

def on_file_saved(editor):
    add_job(editor)

def clear_pylint_warns(editor):
    clear_problems(editor, 'pylint')

qrex = re.compile(r".*?'(.*?)'.*")
dqrex = re.compile(r'.*?"(.*?)".*')
rex = re.compile(
    r'.*?:(?P<lineno>\d+):\s*\[(?P<what>[A-Z]\d{4})(,\s+(?P<where>[^\]]+))?\]\s+(?P<message>.*)')

def parse_name(line, lineno, what, where, message):
    if where and where in line:
        return where

    m = dqrex.match(message)
    if m:
        return m.group(1)

    if where:
        w = where.rsplit('.', 1)[-1]
        if w in line:
            return w

    if where:
        m = qrex.match(where)
        if m:
            return m.group(1)

    return line.strip()

active_process = [None]

def get_problem_list(filename, pylint_cmd):
    import subprocess
    import shlex

    data = open(filename).readlines()

    cmd = ['/usr/bin/env']
    cmd.extend(shlex.split(pylint_cmd))
    cmd.append(filename)

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    active_process[0] = proc
    stdout, stderr = proc.communicate()

    last_line = None

    res = []

    for line in stdout.split('\n'):
        if not line.strip():
            continue
        m = rex.match(line)
        if m:
            d = m.groupdict()
            d['lineno'] = i = int(d['lineno'])
            d['where'] = parse_name(data[i-1], **d)
            res.append(d)
        else:
            if last_line:
                if '^' not in line:
                    continue
                res[-1]['where'] = last_line[line.index('^'):line.rindex('^')+1]
                last_line = None
            else:
                last_line = line

    return [(r['lineno'], r['where'], r['what'] + ' ' + r['message']) for r in res]

def stop_already_runned_jobs():
    proc = active_process[0]
    if proc and proc.poll() is None:
        proc.terminate()
        proc.wait()

def add_job(editor):
    from threading import Thread
    from snaked.util import idle

    def job():
        try:
            problems = get_problem_list(editor.uri, editor.snaked_conf['PYLINT_CMD'])
        except Exception, e:
            idle(editor.message, str(e), 5000)
            return

        idle(mark_problems, editor, 'pylint', problems)

    stop_already_runned_jobs()
    Thread(target=job).start()