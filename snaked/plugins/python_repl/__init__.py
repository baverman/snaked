author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Python REPL'
desc = 'Slim and slick python console'

import os.path
import gtk.gdk, pango
import gtksourceview2
from cPickle import dumps

from snaked.core.prefs import update_view_preferences

def init(injector):
    injector.add_context('python-repl', 'editor',
        lambda e: get_repl_widget(e) if get_repl_widget(e).view.is_focus() else None)

    injector.add_context('python-repl-result-chunk', 'python-repl',
        lambda p: p if cursor_in_result_chunk(p) else None)

    injector.bind('editor', 'python-repl', 'View/Python console', toggle_repl).to('<alt>2')
    injector.bind(('editor', 'python-repl'), 'python-repl-exec',
        'Python/_Execute', exec_code).to('<ctrl>Return', 1)

    injector.bind('python-repl-result-chunk', 'python-repl-squash-result-chunk',
        'Python/S_quash result chunk', squash_result_chunk).to('<ctrl>d')

repl_widget = None
def get_repl_widget(editor):
    global repl_widget
    if repl_widget:
        return repl_widget

    repl_widget = create_repl_widget(editor)

    editor.window.append_panel(repl_widget).on_activate(lambda p: p.view.grab_focus())
    return repl_widget

def create_repl_widget(editor):
    panel = gtk.ScrolledWindow()
    #panel.set_border_width(5)
    panel.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

    panel.view = gtksourceview2.View()
    panel.buffer = gtksourceview2.Buffer()
    panel.view.set_buffer(panel.buffer)
    panel.add(panel.view)
    panel.view.show_all()

    editor.window.manager.set_buffer_prefs(panel.buffer, '', 'python')
    panel.buffer.config.prefs.insert(0, {'show-line-numbers':False, 'highlight-current-line':False})
    update_view_preferences(panel.view, panel.buffer)

    style = panel.buffer.get_style_scheme().get_style('text')

    color = gtk.gdk.color_parse(style.props.background)
    mul = 1.4 if color.value < 0.5 else 1/1.4
    color = str(gtk.gdk.color_from_hsv(color.hue, color.saturation, color.value * mul))

    panel.buffer.create_tag('exec-result', editable=False, scale=0.9, indent=20,
        foreground=style.props.foreground, background=color, background_full_height=True,
        paragraph_background=color, weight=pango.WEIGHT_NORMAL)

    return panel

def toggle_repl(editor):
    repl = get_repl_widget(editor)
    editor.window.popup_panel(repl)

server = None
def get_server_conn(editor):
    global server
    if not server:
        from .executor import run_server
        from ..python.utils import get_executable
        root = editor.project_root
        if not root:
            root = os.path.dirname(editor.uri)
        server = run_server(root, get_executable(editor.conf))

    return server

def cursor_in_result_chunk(panel):
    buf = panel.buffer
    tag = buf.get_tag_table().lookup('exec-result')
    cursor = buf.get_iter_at_mark(buf.get_insert())
    if cursor.has_tag(tag):
        cursor.backward_char()
        return cursor.has_tag(tag)

    return False

def squash_result_chunk(panel):
    buf = panel.buffer
    tag = buf.get_tag_table().lookup('exec-result')
    cursor = buf.get_iter_at_mark(buf.get_insert())

    start = cursor.copy()
    if not start.toggles_tag(tag):
        start.backward_to_tag_toggle(tag)

    end = cursor
    end.forward_to_tag_toggle(tag)
    buf.begin_user_action()
    buf.delete(start, end)
    buf.end_user_action()

def exec_code(editor, panel):
    buf = panel.buffer
    tag = buf.get_tag_table().lookup('exec-result')

    cursor = buf.get_iter_at_mark(buf.get_insert())

    if cursor.has_tag(tag):
        cursor.backward_char()
        if cursor.has_tag(tag):
            editor.window.message('You are at result chunk. Nothing to exec', 'warn', parent=panel.view)
            return True

    start = cursor.copy()
    if not start.toggles_tag(tag):
        start.backward_to_tag_toggle(tag)

    end = cursor
    end.forward_to_tag_toggle(tag)

    source = buf.get_text(start, end).decode('utf-8')

    _, conn = get_server_conn(editor)
    conn.send_bytes(dumps(('run', source, start.get_line() + 1), 2))
    result = conn.recv()

    start = end
    end = start.copy()
    end.forward_to_tag_toggle(tag)
    end_mark = buf.create_mark(None, end)

    buf.begin_user_action()

    if start.starts_line():
        start.backward_char()

    buf.delete(start, end)

    if not result.endswith('\n'):
        result += '\n'

    result = '\n' + result

    buf.insert_with_tags_by_name(start, result, 'exec-result')
    buf.end_user_action()

    buf.place_cursor(buf.get_iter_at_mark(end_mark))
    panel.view.scroll_mark_onscreen(buf.get_insert())
    buf.delete_mark(end_mark)