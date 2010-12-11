import weakref
import gtk
import pango

marked_problems = weakref.WeakKeyDictionary()
attached_editors = weakref.WeakKeyDictionary()

def attach_to_editor(editor):
    """Attach problem tooltips to editor

    It's safe to call function twice on same editor.
    To show problems use :ref:mark_problems

    """
    if editor not in attached_editors:
        attached_editors[editor] = True
        editor.view.connect('query-tooltip', on_query_tooltip)
        editor.view.set_property('has-tooltip', True)

def on_query_tooltip(view, x, y, keyboard_mode, tooltip):
    x, y = view.window_to_buffer_coords(gtk.TEXT_WINDOW_WIDGET, x, y)
    iterator = view.get_iter_at_location(x, y)
    tags = iterator.get_tags()
    if tags:
        tags.reverse()
        for tag in tags:
            try:
                message = marked_problems[view][tag.props.name]
            except KeyError:
                pass
            else:
                box = gtk.EventBox()
                box.set_border_width(5)
                box.add(gtk.Label(message))
                box.show_all()
                tooltip.set_custom(box)

                return True

    return False

def get_tag(editor, prefix, num, message):
    table = editor.buffer.get_tag_table()
    tag_name = '%s_%d' % (prefix, num)

    tag = table.lookup(tag_name)
    if not tag:
        tag = editor.buffer.create_tag(tag_name, underline=pango.UNDERLINE_ERROR)

    marked_problems.setdefault(editor.view, {})[tag_name] = '%s: %s' % (prefix, message)

    return tag

def clear_problems(editor, prefix):
    start, end = editor.buffer.get_bounds()

    sprefix = prefix + '_'
    def clean_tag(tag, data):
        tag_name = tag.props.name
        if tag_name and tag_name.startswith(sprefix):
            try:
                del marked_problems[editor.view][tag_name]
            except KeyError:
                pass

            editor.buffer.remove_tag_by_name(tag_name, start, end)
    editor.buffer.get_tag_table().foreach(clean_tag)

def mark_problems(editor, prefix, problems):
    """Marks problems with error underline

    Also binds messages which can be seen as tooltips to these marks

    :param prefix: problem namespace, e.g. ``python_flakes`` plugin define ``flakes``
                   namespace.
    :param problems: list of (line, name, message) tuples. Where name is suspicious
                      symbol and message is detailed description.

    """
    clear_problems(editor, prefix)

    for num, (line, name, message) in enumerate(problems):
        iter = editor.buffer.get_iter_at_line(line-1)
        nstart = nend = None
        while iter.get_line() == line - 1:
            result = iter.forward_search(name, gtk.TEXT_SEARCH_VISIBLE_ONLY)
            if result is None:
                break
            nstart, nend = result
            if nstart.starts_word() and nend.ends_word():
                break

            iter = nend

        if nstart:
            editor.buffer.apply_tag(get_tag(editor, prefix, num, message), nstart, nend)
        else:
            print "%s: can't find name [%s] on line %d in %s" % (prefix, name, line, editor.uri)
