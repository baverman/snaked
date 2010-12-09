author = 'Anton Bobrov<bobrov@vl.ru>/Fabien Devaux<fdev31@gmail.com>'
name = 'Python flakes/pylint'
desc = 'Basic python linter'
langs = ['python']

import gtk
import pango
import os.path
import weakref

flakes_warnings = weakref.WeakKeyDictionary()

def editor_opened(editor):
    editor.connect('file-saved', on_file_saved)
    editor.view.connect('query-tooltip', on_query_tooltip)
    editor.view.set_property('has-tooltip', True)
    if editor.uri and os.path.exists(editor.uri):
        add_job(editor)

def on_query_tooltip(view, x, y, keyboard_mode, tooltip):
    x, y = view.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET, x, y)
    iterator = view.get_iter_at_location(x, y)
    tags = iterator.get_tags()
    if tags:
        tags.reverse()
        for tag in tags:
            tag_name = tag.get_property('name')
            if tag_name and tag_name.startswith('flakes_'):
                tooltip.set_text(flakes_warnings[view][tag_name])
                return True
    return False

def on_file_saved(editor):
    add_job(editor)

def get_tag(editor, num, message):
    table = editor.buffer.get_tag_table()
    tag_name = 'flakes_%d' % num

    tag = table.lookup(tag_name)
    if not tag:
        tag = editor.buffer.create_tag(tag_name, underline=pango.UNDERLINE_ERROR)

    flakes_warnings.setdefault(editor.view, {})[tag_name] = message

    return tag

def mark_problems(editor, problems):
    start, end = editor.buffer.get_bounds()

    def clean_tag(tag,data):
        tag_name = tag.get_property('name')
        if tag_name and tag_name.startswith('flakes_'):
            editor.buffer.remove_tag_by_name(tag_name,start,end)
    editor.buffer.get_tag_table().foreach(clean_tag,None)

    try:
        flakes_warnings[editor.view].clear()
    except KeyError: pass

    for num, (line, name, message) in enumerate(problems):
        iter = editor.buffer.get_iter_at_line(line-1)
        while iter.get_line() == line - 1:
            result = iter.forward_search(name, gtk.TEXT_SEARCH_VISIBLE_ONLY)
            if result is None:
                break
            nstart, nend = result
            if nstart.starts_word() and nend.ends_word():
                break

            iter = nend

        editor.buffer.apply_tag(get_tag(editor, num, message), nstart, nend)

def get_problem_list(filename):
    import subprocess
    import re

    # pyflakes

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

    # Pylint

    data = open(filename).readlines()

    stdout, stderr = subprocess.Popen(['/usr/bin/env', 'pylint',
        '-f' 'parseable', '-r', 'n', filename],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

    if stderr:
        raise Exception('python_flakes plugin: ' + stderr)

    last_line = None
    qrex = re.compile(r".*?'(.*?)'.*")
    rex = re.compile(r'.*?:(?P<lineno>\d+):\s*\[(?P<what>[A-Z]\d{4})(?P<where>,\s+[^\]]*)?\]\s+(?P<message>.*)')

    res = []

    for line in stdout.split('\n'):
        if not line.strip():
            break
        m = rex.match(line)
        if m:
            d = m.groupdict()
            d['lineno'] = i = int(d['lineno'])
            orig_line = data[i-1]
            if d['where']:
                if d['where'] in orig_line:
                    pass
                elif d['where'].rsplit('.', 1)[-1] in orig_line:
                    d['where'] = d['where'].rsplit('.', 1)[-1]
                else:
                    m = qrex.match(d['where'])
                    if m:
                        d['where'] = m.groups()[0]
                    else:
                        d['where'] = orig_line.strip()
            else:
                d['where'] = orig_line.strip()

            res.append(d)
        else:
            if last_line:
                assert '^' in line
                res[-1]['where'] = last_line[line.index('^'):line.rindex('^')+1]
                last_line = None
            else:
                last_line = line

    for r in res:
        result.append( (r['lineno'], r['where'], r['message']) )

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

        idle(mark_problems, editor, problems)

    Thread(target=job).start()
