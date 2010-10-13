author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Search'
desc = 'Searches words in document'

import gtk
import gtksourceview2

from snaked.util import idle

active_widgets = {}

def init(manager):
    manager.add_shortcut('search', '<ctrl>f', 'Edit', 'Search', search)
    manager.add_shortcut('find-next', '<ctrl>j', 'Edit', 'Find next', find_next)
    manager.add_shortcut('find-prev', '<ctrl>k', 'Edit', 'Find prev', find_prev)

def search(editor):
    if editor in active_widgets:
        widget = active_widgets[editor]
        widget.entry.grab_focus()
    else:
        widget = create_widget(editor)
        active_widgets[editor] = widget
        editor.widget.pack_start(widget, False)
        widget.entry.grab_focus()
        widget.show_all()

def do_find(editor, search_func, dir, start_from=None):
    if editor not in active_widgets:
        return
    
    search = active_widgets[editor].entry.get_text()
    
    iter = start_from
    if not iter:
        if editor.buffer.get_has_selection() and dir == 1:
            iter = editor.buffer.get_iter_at_mark(editor.buffer.get_selection_bound())
        else:
            iter = editor.cursor
            
    bounds = search_func(iter, search,
        gtksourceview2.SEARCH_VISIBLE_ONLY | gtksourceview2.SEARCH_CASE_INSENSITIVE)

    if bounds:
        editor.buffer.select_range(bounds[1], bounds[0])
        editor.view.scroll_to_iter(bounds[0], 0.001, use_align=True, xalign=1.0)
        if start_from:
            editor.message('Wrap search', 800)
        
        return True
    elif not start_from:
        return do_find(editor, search_func, dir, editor.buffer.get_bounds()[dir])
    else:
        editor.message('Text not found')
    
    return False
    
def find_prev(editor):
    do_find(editor, gtksourceview2.iter_backward_search, 1) 

def find_next(editor, grab_focus=False):
    if do_find(editor, gtksourceview2.iter_forward_search, 0) and grab_focus:
        editor.view.grab_focus() 

def create_widget(editor):
    widget = gtk.HBox(False, 10)
    
    label = gtk.Label()
    label.set_text('Search:')
    widget.pack_start(label, False)
    
    entry = gtk.Entry()
    widget.pack_start(entry, False)
    entry.connect('activate', on_search_activate, editor, widget)
    entry.connect('key-press-event', on_key_press, editor, widget)
    
    widget.entry = entry
    
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

def mark_occurences(editor, search):
    cursor = editor.buffer.get_bounds()[0]
    
    while True:
        bounds = gtksourceview2.iter_forward_search(cursor, search,
            gtksourceview2.SEARCH_VISIBLE_ONLY | gtksourceview2.SEARCH_CASE_INSENSITIVE)
        
        if not bounds:
            return
        
        editor.buffer.apply_tag(get_tag(editor), *bounds)
        
        cursor = bounds[1]

def on_search_activate(sender, editor, widget):
    delete_all_marks(editor)
    idle(mark_occurences, editor, sender.get_text())
    editor.push_escape(hide, editor, widget)
    find_next(editor, True)

def on_key_press(sender, event, editor, widget):
    if event.keyval == gtk.keysyms.Escape:
        idle(hide, editor, widget)
        return True
    
    return False
    
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
