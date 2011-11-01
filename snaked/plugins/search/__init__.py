author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Search'
desc = 'Searches words in document'

import re
import weakref

import gtk
import glib

from uxie.utils import idle, refresh_gui
from uxie.escape import Escapable

active_widgets = weakref.WeakKeyDictionary()
search_selections = []
mark_task_is_in_queue = [False]

class SearchSelection(object):
    def __init__(self, search):
        self.search = search

def init(injector):
    injector.add_context('textview-active', 'window',
        lambda w: w.get_focus() if isinstance(w.get_focus(), gtk.TextView) else None)
    injector.add_context('search', 'textview-active',
        lambda t: t if t in active_widgets or search_selections else None)

    injector.bind_accel('textview-active', 'search',  'Edit/_Search#30', '<ctrl>f', search)
    injector.bind_accel('textview-active', 'mark-selection', 'Edit/_Mark', '<ctrl>h', mark_selection)

    injector.bind('search', 'next', 'Edit/Find _next', find_next)
    injector.bind('search', 'prev', 'Edit/Find _prev', find_prev)

    from snaked.core.prefs import add_internal_option
    add_internal_option('SEARCH_IGNORE_CASE', False, 'Ignore case while searching')
    add_internal_option('SEARCH_REGEX', False, 'Use regular expression for searhing')

def get_box(view):
    vbox = view
    while vbox:
        vbox = vbox.get_parent()
        if isinstance(vbox, gtk.VBox):
            return vbox

def search(view):
    if view in active_widgets:
        widget = active_widgets[view]
    else:
        vbox = get_box(view)
        if not vbox:
            view.get_toplevel().message("Can't show search panel", 'warn', parent=view)
            return

        widget = create_widget(view)
        active_widgets[view] = widget
        vbox.pack_start(widget, False)
        view.get_toplevel().push_escape(Escapable(hide, widget, view))
        widget.show_all()

    buf = view.get_buffer()
    if buf.get_has_selection():
        start, end = buf.get_selection_bounds()
        if start.get_line() == end.get_line():
            refresh_gui()

            search = start.get_text(end)
            if widget.regex.get_active():
                search = re.escape(search)

            buf.place_cursor(start)
            widget.entry.set_text(search)
        else:
            widget.entry.grab_focus()
    else:
        widget.entry.grab_focus()

def backward_search(matcher, text, endpos):
    match = None
    for m in matcher.finditer(text):
        if m.end() > endpos:
            return match
        match = m

    return match

def scroll_to_buffer_cursor(view):
    view.scroll_mark_onscreen(view.get_buffer().get_insert())
    ed = getattr(view, 'editor_ref', None)
    if ed:
        ed().clear_cursor()

def do_find(view, dir, start_from=None):
    if view in active_widgets:
        search = active_widgets[view].entry.get_text()
        ignore_case = active_widgets[view].ignore_case.get_active()
        regex = active_widgets[view].regex.get_active()
    elif search_selections:
        search = search_selections[0].search
        ignore_case = False
        regex = False
    else:
        return

    matcher = get_matcher(view, search, ignore_case, regex)
    if not matcher:
        return

    buf = view.get_buffer()
    iter = start_from
    if not iter:
        if buf.get_has_selection() and dir == 1:
            iter = buf.get_iter_at_mark(buf.get_selection_bound())
        else:
            iter = buf.get_iter_at_mark(buf.get_insert())

    utext = buf.get_text(*buf.get_bounds())
    match = None
    if dir == 0:
        match = matcher.search(utext, iter.get_offset())
    else:
        match = backward_search(matcher, utext, iter.get_offset())

    if match:
        bounds = map(buf.get_iter_at_offset, match.span())
        buf.select_range(bounds[1], bounds[0])
        scroll_to_buffer_cursor(view)
        if start_from:
            view.get_toplevel().message('Wrap search', 'info', parent=view)

        return True
    elif not start_from:
        return do_find(view, dir, buf.get_bounds()[dir])
    else:
        view.get_toplevel().message('Text not found', 'info', parent=view)

    return False

def find_prev(view):
    do_find(view, 1)

def find_next(view, grab_focus=False):
    if do_find(view, 0) and grab_focus:
        view.grab_focus()

def create_widget(view):
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
    entry.connect('activate', on_search_activate, view, widget)
    entry.connect_after('changed', on_search_changed, view, widget)

    label = gtk.Label()
    label.set_text('_Replace:')
    label.set_use_underline(True)
    widget.pack_start(label, False)

    entry = gtk.Entry()
    widget.pack_start(entry, False)
    widget.replace_entry = entry
    label.set_mnemonic_widget(entry)
    entry.connect('activate', on_search_activate, view, widget)


    cb = gtk.CheckButton('Ignore _case')
    cb.set_active(view.get_toplevel().manager.conf['SEARCH_IGNORE_CASE'])
    widget.pack_start(cb, False)
    widget.ignore_case = cb

    cb = gtk.CheckButton('Rege_x')
    cb.set_active(view.get_toplevel().manager.conf['SEARCH_REGEX'])
    widget.pack_start(cb, False)
    widget.regex = cb

    label = gtk.Label('Re_place')
    label.set_use_underline(True)
    label.set_padding(10, 1)
    button = gtk.Button()
    button.add(label)
    widget.pack_start(button, False)
    button.connect('clicked', on_replace_activate, view, widget)

    label = gtk.Label('Replace _all')
    label.set_use_underline(True)
    label.set_padding(10, 1)
    button = gtk.Button()
    button.add(label)
    widget.pack_start(button, False)
    button.connect('clicked', on_replace_all_activate, view, widget)
    widget.replace_all = button

    view.connect_after('move-cursor', on_editor_view_move_cursor, widget)
    widget.replace_in_selection = False

    return widget

def get_tag(view):
    buf = view.get_buffer()
    table = buf.get_tag_table()
    tag = table.lookup('search')
    if not tag:
        tag = buf.create_tag('search')
        style = buf.get_style_scheme().get_style('search-match')
        if style:
            if style.props.background_set:
                tag.props.background = style.props.background

            if style.props.foreground_set:
                tag.props.foreground = style.props.foreground
        else:
            style = buf.get_style_scheme().get_style('text')
            if style.props.background_set:
                tag.props.foreground = style.props.background

            if style.props.foreground_set:
                tag.props.background = style.props.foreground

    return tag

def delete_all_marks(view):
    buf = view.get_buffer()
    start, end = buf.get_bounds()
    if buf.get_tag_table().lookup('search'):
        buf.remove_tag_by_name('search', start, end)

def get_matcher(view, search, ignore_case, regex, show_feedback=True):
    flags = re.UNICODE
    if ignore_case:
        flags |= re.IGNORECASE

    if regex:
        try:
            return re.compile(unicode(search), flags)
        except Exception, e:
            if show_feedback:
                view.get_toplevel().message('Bad regex: ' + str(e), 'error', 3000, parent=view)
                if view in active_widgets:
                    idle(active_widgets[view].entry.grab_focus)

            return None
    else:
        return re.compile(re.escape(unicode(search)), flags)

def add_mark_task(view, search, ignore_case, regex, show_feedback=True):
    if not mark_task_is_in_queue[0]:
        mark_task_is_in_queue[0] = True
        idle(mark_occurences, view, search, ignore_case, regex,
            show_feedback, priority=glib.PRIORITY_LOW)

def mark_occurences(view, search, ignore_case, regex, show_feedback=True):
    mark_task_is_in_queue[0] = False
    matcher = get_matcher(view, search, ignore_case, regex, show_feedback)
    if not matcher:
        return False

    count = 0
    buf = view.get_buffer()
    utext = buf.get_text(*buf.get_bounds())
    for m in matcher.finditer(utext):
        buf.apply_tag(get_tag(view),
            *map(buf.get_iter_at_offset, m.span()))

        count += 1

    if count == 1:
        if show_feedback:
            idle(view.get_toplevel().message, 'One occurrence is marked', 'done', parent=view)
    elif count > 1:
        if show_feedback:
            idle(view.get_toplevel().message, '%d occurrences are marked' % count, 'done', parent=view)
    else:
        if show_feedback:
            idle(view.get_toplevel().message, 'Text not found', 'warn', parent=view)
        return False

    return True

def on_search_activate(sender, view, widget):
    delete_all_marks(view)

    editor = getattr(view, 'editor_ref')
    if editor:
        editor().add_spot()

    if mark_occurences(view, widget.entry.get_text(),
            widget.ignore_case.get_active(), widget.regex.get_active()):
        find_next(view, True)

def on_search_changed(sender, view, widget):
    search = widget.entry.get_text()
    idle(delete_all_marks, view)

    if search and ( len(search) != 1 or ( not search.isdigit() and not search.isalpha()
            and not search.isspace() ) ):
        idle(add_mark_task, view, search,
                widget.ignore_case.get_active(), widget.regex.get_active(), False)

def hide(widget, view):
    delete_all_marks(view)

    try:
        del active_widgets[view]
    except KeyError:
        pass

    if widget and widget.get_parent():
        get_box(view).remove(widget)
        widget.destroy()

        conf = view.get_toplevel().manager.conf
        conf['SEARCH_IGNORE_CASE'] = widget.ignore_case.get_active()
        conf['SEARCH_REGEX'] = widget.regex.get_active()

    view.grab_focus()

def mark_selection(view):
    buf = view.get_buffer()
    if not buf.get_has_selection():
        view.get_toplevel().message('Select something', 'warn', parent=view)
        return

    if search_selections:
        search_selections[:] = []

    delete_all_marks(view)

    occur = SearchSelection(buf.get_text(*buf.get_selection_bounds()))
    search_selections.append(occur)

    def remove_all(view, occur):
        search_selections[:] = []
        delete_all_marks(view)

    mark_occurences(view, occur.search, False, False)
    view.get_toplevel().push_escape(Escapable(remove_all, view, occur))

def on_replace_activate(button, view, widget):
    if view not in active_widgets:
        return

    search = active_widgets[view].entry.get_text()
    ignore_case = active_widgets[view].ignore_case.get_active()
    regex = active_widgets[view].regex.get_active()
    replace = unicode(active_widgets[view].replace_entry.get_text())

    matcher = get_matcher(view, search, ignore_case, regex)
    if not matcher:
        return

    buf = view.get_buffer()
    utext = buf.get_text(*buf.get_bounds())

    if buf.get_has_selection():
        iter = buf.get_selection_bounds()[0]
    else:
        iter = buf.get_iter_at_mark(buf.get_insert())

    match = matcher.search(utext, iter.get_offset())
    if not match:
        view.get_toplevel().message('Replace what?', 'warn', parent=view)
        return

    start, end = map(buf.get_iter_at_offset, match.span())
    buf.begin_user_action()
    buf.place_cursor(start)
    buf.delete(start, end)
    buf.insert_at_cursor(match.expand(replace).encode('utf-8'))
    buf.end_user_action()

    scroll_to_buffer_cursor(view)

def on_replace_all_activate(button, view, widget):
    if view not in active_widgets:
        return

    search = active_widgets[view].entry.get_text()
    ignore_case = active_widgets[view].ignore_case.get_active()
    regex = active_widgets[view].regex.get_active()
    replace = unicode(active_widgets[view].replace_entry.get_text())

    matcher = get_matcher(view, search, ignore_case, regex)
    if not matcher:
        return

    buf = view.get_buffer()
    utext = buf.get_text(*buf.get_bounds())
    cursor = buf.get_iter_at_mark(buf.get_insert())

    line, offset = cursor.get_line(), cursor.get_line_offset()

    if active_widgets[view].replace_in_selection:
        start, end = buf.get_selection_bounds()
        start.order(end)
    else:
        start, end = buf.get_bounds()

    end_mark = buf.create_mark(None, end)

    buf.begin_user_action()
    buf.place_cursor(start)
    count = 0
    while True:
        match = matcher.search(utext, cursor.get_offset())
        if not match:
            break

        start, end = map(buf.get_iter_at_offset, match.span())
        if end.compare(buf.get_iter_at_mark(end_mark)) > 0:
            break

        buf.place_cursor(start)
        buf.delete(start, end)
        buf.insert_at_cursor(match.expand(replace).encode('utf-8'))
        count += 1

    buf.end_user_action()

    if not count:
        view.get_toplevel().message('Nothing to replace', 'info', parent=view)
    elif count == 1:
        view.get_toplevel().message('One occurrence was replaced', 'done', parent=view)
    else:
        view.get_toplevel().message('%d occurrences were replaced' % count, 'done', parent=view)

    cursor = buf.get_iter_at_mark(buf.get_insert())
    cursor.set_line(line)
    cursor.set_line_offset(offset)
    buf.place_cursor(cursor)
    scroll_to_buffer_cursor(view)
    view.grab_focus()

def on_editor_view_move_cursor(view, step, count, selection, widget):
    if selection:
        r = view.get_buffer().get_selection_bounds()
        new_state = r and r[0].get_line() != r[1].get_line()
    else:
        new_state = False

    if widget.replace_in_selection != new_state:
        widget.replace_in_selection = new_state
        if new_state:
            widget.replace_all.set_label("Replace in se_lection")
        else:
            widget.replace_all.set_label("Replace _all")
