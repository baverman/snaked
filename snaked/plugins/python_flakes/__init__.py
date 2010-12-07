author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Python flakes'
desc = 'Basic python linter'

import gtk
import pango
import os.path

langs = ['python']

def editor_opened(editor):
    editor.connect('file-saved', on_file_saved)
    editor.view.connect('query-tooltip', on_query_tooltip)
    editor.view.set_property('has-tooltip', True)
    if editor.uri and os.path.exists(editor.uri):
        add_job(editor)

def on_query_tooltip(view,x,y,keyboard_mode,tooltip):
    '''
    Show error message as tooltip
    Putting tooltip in the tag name is dirty, though
    '''
    x, y = view.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET, x, y)
    iterator = view.get_iter_at_location(x,y)
    tags = iterator.get_tags()
    if tags:
        tags.reverse()
        for tag in tags:
            tag_name = tag.get_property('name')
            if tag_name and tag_name.startswith('flakes_'):
                tooltip.set_text(tag_name[7:])
                return True
    return False

def on_file_saved(editor):
    add_job(editor)

def get_tag(editor,message):
    table = editor.buffer.get_tag_table()
    message = message[:min(255,len(message))]
    tag = table.lookup('flakes_%s' % message)
    if not tag:
        tag = editor.buffer.create_tag('flakes_%s' % message, underline=pango.UNDERLINE_ERROR)

    return tag

def mark_problems(editor, problems):
    start, end = editor.buffer.get_bounds()

    def clean_tag(tag,data):
        tag_name = tag.get_property('name')
        if tag_name and tag_name.startswith('flakes_'):
            editor.buffer.remove_tag_by_name(tag_name,start,end)
    editor.buffer.get_tag_table().foreach(clean_tag,None)

    for line, name, message in problems:
        iter = editor.buffer.get_iter_at_line(line-1)
        while iter.get_line() == line - 1:
            result = iter.forward_search(name, gtk.TEXT_SEARCH_VISIBLE_ONLY)
            if result is None:
                break
            nstart, nend = result
            if nstart.starts_word() and nend.ends_word():
                break

            iter = nend
        editor.buffer.apply_tag(get_tag(editor,message), nstart, nend)

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

        idle(mark_problems, editor, problems)

    Thread(target=job).start()
