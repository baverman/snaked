author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Search'
desc = 'Searches words in document'

import re
import weakref
import gtk
from snaked.util import idle

active_widgets = weakref.WeakKeyDictionary()
search_selections = []

class SearchSelection(object):
    def __init__(self, search):
        self.search = search

def init(manager):
    manager.add_shortcut('search', '<ctrl>f', 'Edit', 'Search', search)
    manager.add_shortcut('find-next', '<ctrl>j', 'Edit', 'Find next', find_next)
    manager.add_shortcut('find-prev', '<ctrl>k', 'Edit', 'Find prev', find_prev)
    manager.add_shortcut('mark-selection', '<ctrl>h', 'Edit',
        'Mark selection occurrences', mark_selection)

def search(editor):
    if editor in active_widgets:
        widget = active_widgets[editor]
        widget.entry.grab_focus()
    else:
        widget = create_widget(editor)
        active_widgets[editor] = widget
        editor.widget.pack_start(widget, False)
        widget.entry.grab_focus()
        editor.push_escape(hide, widget)
        widget.show_all()

def backward_search(matcher, text, endpos):
    match = None
    for m in matcher.finditer(text):
        if m.end() > endpos:
            return match
        match = m

    return match

def do_find(editor, dir, start_from=None):
    if editor in active_widgets:
        search = active_widgets[editor].entry.get_text()
        ignore_case = active_widgets[editor].ignore_case.get_active()
        regex = active_widgets[editor].regex.get_active()
    elif search_selections:
        search = search_selections[0].search
        ignore_case = False
        regex = False
    else:
        return

    matcher = get_matcher(editor, search, ignore_case, regex)
    if not matcher:
        return

    iter = start_from
    if not iter:
        if editor.buffer.get_has_selection() and dir == 1:
            iter = editor.buffer.get_iter_at_mark(editor.buffer.get_selection_bound())
        else:
            iter = editor.cursor

    match = None
    if dir == 0:
        match = matcher.search(editor.utext, iter.get_offset())
    else:
        match = backward_search(matcher, editor.utext, iter.get_offset())

    if match:
        bounds = map(editor.buffer.get_iter_at_offset, match.span())
        editor.buffer.select_range(bounds[1], bounds[0])
        editor.view.scroll_to_iter(bounds[0], 0.001, use_align=True, xalign=1.0)
        if start_from:
            editor.message('Wrap search', 800)

        return True
    elif not start_from:
        return do_find(editor, dir, editor.buffer.get_bounds()[dir])
    else:
        editor.message('Text not found')

    return False

def find_prev(editor):
    do_find(editor, 1)

def find_next(editor, grab_focus=False):
    if do_find(editor, 0) and grab_focus:
        editor.view.grab_focus()

def create_widget(editor):
    widget = gtk.HBox(False, 10)
    widget.set_border_width(3)

    label = gtk.Label()
    label.set_text('_Search:')
    label.set_use_underline(True)
    widget.pack_start(label, False)

    entry = gtk.Entry()
    widget.pack_start(entry, False)
    widget.entry = entry
    label.set_mnemonic_widget(entry)
    entry.connect('activate', on_search_activate, editor, widget)


    label = gtk.Label()
    label.set_text('_Replace:')
    label.set_use_underline(True)
    widget.pack_start(label, False)

    entry = gtk.Entry()
    widget.pack_start(entry, False)
    widget.replace_entry = entry
    label.set_mnemonic_widget(entry)
    entry.connect('activate', on_search_activate, editor, widget)


    cb = gtk.CheckButton('Ignore _case')
    widget.pack_start(cb, False)
    widget.ignore_case = cb

    cb = gtk.CheckButton('Rege_x')
    widget.pack_start(cb, False)
    widget.regex = cb

    label = gtk.Label('Re_place')
    label.set_use_underline(True)
    label.set_padding(10, 1)
    button = gtk.Button()
    button.add(label)
    widget.pack_start(button, False)
    button.connect('activate', on_replace_activate, editor, widget)

    label = gtk.Label('Replace _all')
    label.set_use_underline(True)
    label.set_padding(10, 1)
    button = gtk.Button()
    button.add(label)
    widget.pack_start(button, False)
    button.connect('activate', on_replace_all_activate, editor, widget)

    return widget

def get_tag(editor):
    table = editor.buffer.get_tag_table()
    tag = table.lookup('search')
    if not tag:
        style = editor.buffer.get_style_scheme().get_style('search-match')
        tag = editor.buffer.create_tag('search')

        if style.props.background_set:
            tag.props.background = style.props.background

        if style.props.foreground_set:
            tag.props.foreground = style.props.foreground

    return tag

def delete_all_marks(editor):
    start, end = editor.buffer.get_bounds()
    if editor.buffer.get_tag_table().lookup('search'):
        editor.buffer.remove_tag_by_name('search', start, end)

def get_matcher(editor, search, ignore_case, regex):
    flags = re.UNICODE
    if ignore_case:
        flags |= re.IGNORECASE

    if regex:
        try:
            return re.compile(unicode(search), flags)
        except Exception, e:
            editor.message('Bad regex: ' + str(e), 3000)
            if editor in active_widgets:
                idle(active_widgets[editor].entry.grab_focus)
            return None
    else:
        return re.compile(re.escape(unicode(search)), flags)

def mark_occurences(editor, search, ignore_case, regex):
    matcher = get_matcher(editor, search, ignore_case, regex)
    if not matcher:
        return False

    count = 0
    for m in matcher.finditer(editor.utext):
        editor.buffer.apply_tag(get_tag(editor),
            *map(editor.buffer.get_iter_at_offset, m.span()))

        count += 1

    if count == 1:
        idle(editor.message, 'One occurrence is marked')
    elif count > 1:
        idle(editor.message, '%d occurrences are marked' % count)
    else:
        idle(editor.message, 'Text not found')
        return False

    return True

def on_search_activate(sender, editor, widget):
    delete_all_marks(editor)
    if mark_occurences(editor, widget.entry.get_text(),
            widget.ignore_case.get_active(), widget.regex.get_active()):
        find_next(editor, True)

def hide(editor, widget):
    delete_all_marks(editor)

    try:
        del active_widgets[editor]
    except KeyError:
        pass

    if widget and widget.get_parent():
        editor.widget.remove(widget)
        widget.destroy()

    editor.view.grab_focus()

def mark_selection(editor):
    if not editor.buffer.get_has_selection():
        editor.message('Select something')
        return

    if search_selections:
        search_selections[:] = []

    delete_all_marks(editor)

    occur = SearchSelection(editor.buffer.get_text(*editor.buffer.get_selection_bounds()))
    search_selections.append(occur)

    def remove_all(editor, occur):
        search_selections[:] = []
        delete_all_marks(editor)

    mark_occurences(editor, occur.search, False, False)
    editor.push_escape(remove_all, occur)

def on_replace_activate(button, editor, widget):
    if editor not in active_widgets:
        return

    search = active_widgets[editor].entry.get_text()
    ignore_case = active_widgets[editor].ignore_case.get_active()
    regex = active_widgets[editor].regex.get_active()
    replace = unicode(active_widgets[editor].replace_entry.get_text())

    matcher = get_matcher(editor, search, ignore_case, regex)
    if not matcher:
        return

    if editor.buffer.get_has_selection():
        iter = editor.buffer.get_selection_bounds()[0]
    else:
        iter = editor.cursor

    match = matcher.search(editor.utext, iter.get_offset())
    if not match:
        editor.message('Replace what?')
        return

    start, end = map(editor.buffer.get_iter_at_offset, match.span())
    editor.buffer.begin_user_action()
    editor.buffer.place_cursor(start)
    editor.buffer.delete(start, end)
    editor.buffer.insert_at_cursor(match.expand(replace).encode('utf-8'))
    editor.buffer.end_user_action()

    idle(editor.scroll_to_cursor)

def on_replace_all_activate(button, editor, widget):
    if editor not in active_widgets:
        return

    search = active_widgets[editor].entry.get_text()
    ignore_case = active_widgets[editor].ignore_case.get_active()
    regex = active_widgets[editor].regex.get_active()
    replace = unicode(active_widgets[editor].replace_entry.get_text())

    matcher = get_matcher(editor, search, ignore_case, regex)
    if not matcher:
        return

    line, offset = editor.cursor.get_line(), editor.cursor.get_line_offset()

    editor.buffer.begin_user_action()
    editor.buffer.place_cursor(editor.buffer.get_bounds()[0])
    count = 0
    while True:
        match = matcher.search(editor.utext, editor.cursor.get_offset())
        if not match:
            break

        start, end = map(editor.buffer.get_iter_at_offset, match.span())
        editor.buffer.place_cursor(start)
        editor.buffer.delete(start, end)
        editor.buffer.insert_at_cursor(match.expand(replace).encode('utf-8'))
        count += 1

    editor.buffer.end_user_action()

    if not count:
        editor.message('Nothing to replace')
    elif count == 1:
        editor.message('One occurrence was replaced')
    else:
        editor.message('%d occurrences were replaced' % count)

    cursor = editor.cursor
    cursor.set_line(line)
    cursor.set_line_offset(offset)
    editor.buffer.place_cursor(cursor)
    editor.scroll_to_cursor()