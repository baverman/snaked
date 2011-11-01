import os
import os.path

title_handlers = {}
fsm_cache = {}
title_contexts = {}
wtitle_contexts = {}

def init(injector):
    from .prefs import add_option

    add_option('TAB_TITLE_FORMAT', '%modified{%pypkg|%name2}{%writeable|[ro]}',
        'Default format string for tab titles')

    add_option('WINDOW_TITLE_FORMAT',
        '%modified{%project|NOP}:{%path|%fullpath}{%writeable|[ro]}',
        'Default format string for window title')

    add_title_handler('name', name_handler)
    add_title_handler('name2', name2_handler)
    add_title_handler('project', project_handler)
    add_title_handler('path', path_handler)
    add_title_handler('fullpath', fullpath_handler)
    add_title_handler('writeable', writable_handler)
    add_title_handler('modified', modified_handler)

    injector.on_ready('editor-with-new-buffer-created', editor_created)

def editor_created(editor):
    editor.connect('get-title', on_editor_get_title)
    editor.connect('get-window-title', on_editor_get_window_title)

def get_format_from_context(editor, context):
    return editor.window.manager.get_context_manager(
        editor.project_root).get_first(context, editor.uri)

def on_editor_get_title(editor):
    format = get_format_from_context(editor, 'title')
    if not format:
        format = editor.conf['TAB_TITLE_FORMAT']

    return get_title(editor, format)

def on_editor_get_window_title(editor):
    format = get_format_from_context(editor, 'wtitle')
    if not format:
        format = editor.conf['WINDOW_TITLE_FORMAT']

    return get_title(editor, format)

def add_title_handler(name, callback):
    title_handlers[name] = callback

def name_handler(editor):
    """Return file basename"""
    return os.path.basename(editor.uri)

def name2_handler(editor):
    """Return file basename with descending directory name"""
    dirname, basename = os.path.split(editor.uri)
    return os.path.basename(dirname) + '/' + basename

def project_handler(editor):
    """Return project name (basename of project path). None if project is not defined"""
    root = editor.project_root
    if root:
        return os.path.basename(root)

def writable_handler(editor):
    """Return empty string if file is writeable else None. Useful for ``ro`` marks"""
    path = editor.uri if os.path.exists(editor.uri) else os.path.dirname(editor.uri)
    if os.access(path, os.W_OK):
        return ''

def modified_handler(editor):
    """Return asteriks if editor's buffer is changed, empty string otherwise"""
    return '*' if editor.buffer.get_modified() else ''

def empty_handler(editor):
    """Always return None"""
    return None

def path_handler(editor):
    """Return file path within project. None if project is not defined"""
    root = editor.project_root
    if root:
        return os.path.relpath(editor.uri, root)

def fullpath_handler(editor):
    """Return absolute file path"""
    return editor.uri

def get_title(editor, format):
    try:
        fsm = fsm_cache[format]
    except KeyError:
        fsm = fsm_cache[format] = create_fsm(format)

    return fsm(editor)

def create_alternative_handler(handlers):
    def handler(editor):
        for h, fstr in handlers:
            if h is None:
                return fstr

            value = h(editor)
            if value is not None:
                return fstr % value

        return ''

    return handler

def create_fsm(format):
    import re

    alt_matcher = re.compile('\{(.+?)\}')
    handler_matcher = re.compile('%([_a-zA-Z0-9]+)')
    handlers = {}
    hid = [0]

    def replace_alt(match):
        hlist = []
        for m in match.group(1).split('|'):
            hm = handler_matcher.search(m)
            if hm:
                hlist.append((title_handlers.get(hm.group(1), empty_handler),
                    handler_matcher.sub('%s', m)))
            else:
                hlist.append((None, m))

        hid[0] += 1
        hid_name = 'alt_%d' % hid[0]
        handlers[hid_name] = create_alternative_handler(hlist)
        return '%%(%s)s' % hid_name

    def replace_handlers(match):
        hname = match.group(1)
        handlers[hname] = title_handlers.get(hname, empty_handler)
        return '%%(%s)s' % hname

    result = alt_matcher.sub(replace_alt, format)
    result = handler_matcher.sub(replace_handlers, result)

    def root(editor):
        rdict = {}
        for k, h in handlers.items():
            value = h(editor)
            if value is None:
                value = ''
            rdict[k] = value

        return result % rdict

    return root