author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Search'
desc = 'Searches words in document'

import re
import weakref

import gtk
import glib

from uxie.utils import idle, refresh_gui, widget_is_child_of, text_buffer_user_action
from uxie.escape import Escapable

active_search_widgets = weakref.WeakKeyDictionary()
active_replace_widgets = weakref.WeakKeyDictionary()
search_selections = []
mark_task_is_in_queue = False

class SearchSelection(object):
    def __init__(self, search):
        self.search = search

def init(injector):
    injector.add_context('search', 'ctx_getter', search_context)
    injector.add_context('replace', 'ctx_getter', replace_context)
    injector.add_context('replace-all', 'replace',
        lambda view: None if view_has_multiline_selection(view) else view)
    injector.add_context('replace-in-selection', 'replace',
        lambda view: view if view_has_multiline_selection(view) else None)

    injector.bind('textview-active', 'search',  'Edit/_Search#30/_Find', search).to('<ctrl>f')
    injector.bind('textview-active', 'mark-selection', 'Edit/Search/_Mark', mark_selection).to('<ctrl>h')
    injector.bind('search', 'replace',  'Edit/Search/_Replace', replace).to('<ctrl>r')
    injector.bind('replace', 'replace-next', 'Edit/Search/Replace and goto ne_xt',
        replace_next).to('<ctrl>Return', 10)
    injector.bind('replace-all', 'replace-all', 'Edit/Search/Replace _all',
        replace_all, False).to('<ctrl><shift>Return', 10)
    injector.bind('replace-in-selection', 'replace-in-selection',
        'Edit/Search/Replace in _selection', replace_all, True).to('<ctrl><shift>Return', 10)

    injector.bind_check('search', 'search-ignore-case', 'Edit/Search/_Ignore case',
        ignore_case).to('<alt>i')

    injector.bind_check('search', 'search-use-regex', 'Edit/Search/Use _RegEx',
        use_regex).to('<alt>r')

    injector.bind('search', 'next', 'Edit/Search/Find _next', find_next)
    injector.bind('search', 'prev', 'Edit/Search/Find _prev', find_prev)

    from snaked.core.prefs import add_internal_option
    add_internal_option('SEARCH_IGNORE_CASE', False)
    add_internal_option('SEARCH_REGEX', False)
    add_internal_option('LAST_SEARCHES', list)
    add_internal_option('LAST_REPLACES', list)

def search_context(ctx_getter):
    view = ctx_getter('textview-active')
    if view:
        if (search_selections or view in active_search_widgets):
            return view
    else:
        window = ctx_getter('window')
        focused_widget = window.get_focus()
        for view, search_widget in active_search_widgets.iteritems():
            if widget_is_child_of(focused_widget, search_widget):
                return view

def replace_context(ctx_getter):
    view = ctx_getter('textview-active')
    if view:
        if view in active_replace_widgets:
            return view
    else:
        window = ctx_getter('window')
        focused_widget = window.get_focus()
        for view, replace_widget in active_replace_widgets.iteritems():
            if widget_is_child_of(focused_widget, replace_widget):
                return view

def view_has_multiline_selection(view):
    buf = view.get_buffer()
    if buf.get_has_selection():
        start, end = buf.get_selection_bounds()
        return start.get_line() != end.get_line()
    else:
        return False

def search(view):
    if view in active_search_widgets:
        widget = active_search_widgets[view]
    else:
        viewref = weakref.ref(view)
        def on_cancel(_feedback):
            view = viewref()
            if view:
                active_search_widgets.pop(view, None)
                delete_all_marks(view)
                view.grab_focus()

        widget = create_search_widget(view)
        active_search_widgets[view] = widget

        window = view.get_toplevel()
        window.push_escape(
            window.feedback(widget, priority=5, parent=view).on_cancel(on_cancel), 5)

    buf = view.get_buffer()
    if buf.get_has_selection():
        start, end = buf.get_selection_bounds()
        if start.get_line() == end.get_line():
            refresh_gui()

            search = start.get_text(end)
            if is_regex(view):
                search = re.escape(search)

            buf.place_cursor(start)
            update_last_search(view, search)
            widget.entry.set_text(search)
        else:
            set_last_search(view, widget.entry)
            widget.entry.grab_focus()
    else:
        set_last_search(view, widget.entry)
        widget.entry.grab_focus()

def set_last_search(view, entry):
    searches = entry.get_toplevel().manager.conf['LAST_SEARCHES']
    try:
        search, icase, regex = searches[0]
    except IndexError:
        pass
    else:
        view.get_toplevel().manager.conf['SEARCH_REGEX'] = regex
        view.get_toplevel().manager.conf['SEARCH_IGNORE_CASE'] = icase
        if view in active_search_widgets:
            update_state_widget(view, active_search_widgets[view])
        entry.set_text(search)

def update_last_search(view, search, icase=None, regex=None):
    if not search:
        return

    if icase is None:
        icase = is_icase(view)

    if regex is None:
        regex = is_regex(view)

    searches = view.get_toplevel().manager.conf['LAST_SEARCHES']
    value = search, icase, regex
    while True:
        try:
            searches.remove(value)
        except ValueError:
            break

    searches.insert(0, value)
    searches[:] = searches[:30]

def replace(view):
    if view in active_replace_widgets:
        widget = active_replace_widgets[view]
    else:
        viewref = weakref.ref(view)
        def on_cancel(_feedback):
            view = viewref()
            if view:
                active_replace_widgets.pop(view, None)
                view.grab_focus()

        widget = create_replace_widget(view)
        active_replace_widgets[view] = widget

        window = view.get_toplevel()
        window.push_escape(
            window.feedback(widget, priority=6, parent=view).on_cancel(on_cancel), 5)

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

def get_find_params(view):
    if view in active_search_widgets:
        search = active_search_widgets[view].entry.get_text()
        ignore_case = is_icase(view)
        regex = is_regex(view)
    elif search_selections:
        search = search_selections[0].search
        ignore_case = False
        regex = False
    else:
        return None

    return search, ignore_case, regex

def do_find(view, dir, start_from=None):
    search, ignore_case, regex = get_find_params(view)
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

    utext = buf.get_text(*buf.get_bounds()).decode('utf-8')
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

def update_state_widget(view, widget):
    text = ''
    if is_icase(view):
        text += 'I'

    if is_regex(view):
        text += 'R'

    widget.opt_state.set_markup('<b>%s</b>' % text)

def create_search_widget(view):
    widget = gtk.EventBox()

    frame = gtk.Frame()
    widget.add(frame)

    hbox = gtk.HBox(False, 3)
    frame.add(hbox)

    hbox.pack_start(gtk.image_new_from_stock(gtk.STOCK_FIND, gtk.ICON_SIZE_SMALL_TOOLBAR), False)

    widget.opt_state = gtk.Label()
    hbox.pack_start(widget.opt_state, False)
    update_state_widget(view, widget)

    entry = gtk.Entry()
    hbox.pack_start(entry, False)
    widget.entry = entry
    entry.connect('activate', on_search_activate, view, widget)
    entry.connect_after('changed', on_search_changed, view, widget)

    return widget

def create_replace_widget(view):
    widget = gtk.EventBox()

    frame = gtk.Frame()
    widget.add(frame)

    hbox = gtk.HBox(False, 3)
    frame.add(hbox)

    hbox.pack_start(gtk.image_new_from_stock(
        gtk.STOCK_FIND_AND_REPLACE, gtk.ICON_SIZE_SMALL_TOOLBAR), False)

    widget.entry = entry = gtk.Entry()
    hbox.pack_start(entry, False)
    entry.connect('activate', on_replace_activate, view)

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
                if view in active_search_widgets:
                    idle(active_search_widgets[view].entry.grab_focus)

            return None
    else:
        return re.compile(re.escape(unicode(search)), flags)

def add_mark_task(view, search, ignore_case, regex, show_feedback=True):
    global mark_task_is_in_queue
    if not mark_task_is_in_queue:
        mark_task_is_in_queue = True
        idle(mark_occurences, view, search, ignore_case, regex,
            show_feedback, priority=glib.PRIORITY_LOW)

def mark_occurences(view, search, ignore_case, regex, show_feedback=True):
    global mark_task_is_in_queue
    mark_task_is_in_queue = False
    matcher = get_matcher(view, search, ignore_case, regex, show_feedback)
    if not matcher:
        return False

    count = 0
    buf = view.get_buffer()
    utext = buf.get_text(*buf.get_bounds()).decode('utf-8')
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

def is_icase(view):
    return view.get_toplevel().manager.conf['SEARCH_IGNORE_CASE']

def is_regex(view):
    return view.get_toplevel().manager.conf['SEARCH_REGEX']

def use_regex(view, is_set):
    if is_set:
        view.get_toplevel().manager.conf['SEARCH_REGEX'] = not is_regex(view)
        if view in active_search_widgets:
            update_state_widget(view, active_search_widgets[view])
    else:
        return is_regex(view)

def ignore_case(view, is_set):
    if is_set:
        view.get_toplevel().manager.conf['SEARCH_IGNORE_CASE'] = not is_icase(view)
        if view in active_search_widgets:
            update_state_widget(view, active_search_widgets[view])
    else:
        return is_icase(view)

def on_search_activate(sender, view, widget):
    delete_all_marks(view)

    editor = getattr(view, 'editor_ref', None)
    if editor:
        editor().add_spot()

    update_last_search(view, widget.entry.get_text())
    if mark_occurences(view, widget.entry.get_text(), is_icase(view), is_regex(view)):
        find_next(view, True)

def on_search_changed(sender, view, widget):
    search = widget.entry.get_text()
    idle(delete_all_marks, view)

    if search and ( len(search) != 1 or ( not search.isdigit() and not search.isalpha()
            and not search.isspace() ) ):
        idle(add_mark_task, view, search, is_icase(view), is_regex(view), False)

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

    update_last_search(view, occur.search, False, False)
    mark_occurences(view, occur.search, False, False)
    view.get_toplevel().push_escape(Escapable(remove_all, view, occur), 5)

def find_search_tag(view, start, wrap):
    tag = get_tag(view)
    it = start.copy()
    while True:
        if it.toggles_tag(tag) and it.has_tag(tag):
            return it

        if not it.forward_to_tag_toggle(tag) or it.is_end():
            if wrap:
                wrap = False
                it = view.get_buffer().get_bounds()[0]
            else:
                return None

def get_search_tag_end(view, start):
    tag = get_tag(view)
    it = start.copy()
    if it.forward_to_tag_toggle(tag):
        return it
    else:
        raise Exception('Something goes wrong')

def do_replace(view, matcher, start, replace):
    end = get_search_tag_end(view, start)
    utext = start.get_text(end).decode('utf-8')

    match = matcher.search(utext)
    if not match or match.start() != 0:
        return False

    buf = view.get_buffer()
    buf.place_cursor(start)
    buf.delete(start, end)
    buf.insert_at_cursor(match.expand(replace))

def get_leftmost_cursor(buf):
    if buf.get_has_selection():
        return buf.get_selection_bounds()[0]
    else:
        return buf.get_iter_at_mark(buf.get_insert())

def on_replace_activate(_entry, view):
    replace_next(view)

def replace_next(view):
    buf = view.get_buffer()
    cursor = get_leftmost_cursor(buf)
    it = find_search_tag(view, cursor, True)
    if it:
        view.grab_focus()
        if it.equal(cursor):
            matcher = get_matcher(view, *get_find_params(view))
            replace = unicode(active_replace_widgets[view].entry.get_text())
            with text_buffer_user_action(buf):
                do_replace(view, matcher, it, replace)

            it = find_search_tag(view, buf.get_iter_at_mark(buf.get_insert()), True)

        if it:
            buf.place_cursor(it)

        scroll_to_buffer_cursor(view)
    else:
        view.get_toplevel().message('Replace what?', 'warn', parent=view)

def replace_all(view, is_selection):
    matcher = get_matcher(view, *get_find_params(view))
    replace = unicode(active_replace_widgets[view].entry.get_text())

    if not matcher:
        return

    buf = view.get_buffer()
    if is_selection:
        start, end = buf.get_selection_bounds()
        start.order(end)
    else:
        start, end = buf.get_bounds()

    end_mark = buf.create_mark(None, end)

    cursor = buf.get_iter_at_mark(buf.get_insert())
    line, offset = cursor.get_line(), cursor.get_line_offset()

    count = 0
    it = start
    with text_buffer_user_action(buf):
        while True:
            it = find_search_tag(view, it, False)
            if not it or it.compare(buf.get_iter_at_mark(end_mark)) > 0:
                break

            do_replace(view, matcher, it, replace)
            it = buf.get_iter_at_mark(buf.get_insert())
            count += 1

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