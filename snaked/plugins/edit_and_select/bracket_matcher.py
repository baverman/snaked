import pango

from snaked.util import idle

brackets = {
    '(': (')', 1),
    ')': ('(', -1),
    '[': (']', 1),
    ']': ('[', -1),
    '{': ('}', 1),
    '}': ('{', -1),
}

matched_tags = [None]
highlight_task_added = [False]

def add_highlight_task(buf):
    if not highlight_task_added[0]:
        highlight_task_added[0] = True
        idle(highlight_matching_brackets, buf)

def attach(editor):
    editor.buffer.set_highlight_matching_brackets(False)
    editor.view.connect_after('move-cursor', on_view_move_cursor)
    editor.buffer.connect_after('changed', on_buffer_changed)

def reset_tags(buf):
    if matched_tags[0] and buf.get_tag_table().lookup(matched_tags[0]):
        start, end = buf.get_bounds()
        buf.remove_tag_by_name(matched_tags[0], start, end)
        matched_tags[0] = None

def highlight_matching_brackets(buf):
    """:type buf: gtk.TextBuffer()"""
    highlight_task_added[0] = False

    iter = buf.get_iter_at_mark(buf.get_insert())
    char = iter.get_char()
    piter = iter.copy()
    if piter.backward_cursor_position():
        pchar = piter.get_char()
    else:
        pchar = ''

    lbr = rbr = None
    if char in brackets:
        rbr, rd = brackets[char]

    if pchar in brackets:
        lbr, ld = brackets[pchar]

    reset_tags(buf)

    if not lbr and not rbr:
        return

    if lbr == char:
        return

    if lbr:
        mark_brackets(buf, piter, find_bracket(piter, lbr, pchar, ld))

    if rbr:
        mark_brackets(buf, iter, find_bracket(iter, rbr, char, rd))

def on_view_move_cursor(view, step_size, count, extend_selection):
    add_highlight_task(view.get_buffer())

def on_buffer_changed(buf):
    add_highlight_task(buf)

def find_bracket(from_iter, br, obr, dir):
    limit = 500
    iter = from_iter.copy()
    depth = 1
    while limit > 0:
        if not iter.forward_cursor_positions(dir):
            break

        c = iter.get_char()
        if c == br:
            depth -= 1
        elif c == obr:
            depth += 1

        if depth == 0:
            return iter

        limit -= 1

    return None

def mark_brackets(buf, start, end):
    type = 'bracket-match' if end else 'bracket-mismatch'
    matched_tags[0] = type
    tag = get_tag(buf, type)

    mark_bracket(buf, start, tag)

    if end:
        mark_bracket(buf, end, tag)

def mark_bracket(buf, iter, tag):
    end = iter.copy()
    end.forward_char()

    buf.apply_tag(tag, iter, end)

def get_tag(buf, type):
    table = buf.get_tag_table()
    tag = table.lookup(type)
    if not tag:
        style = buf.get_style_scheme().get_style(type)
        tag = buf.create_tag(type)

        if style.props.background_set:
            tag.props.background = style.props.background

        if style.props.foreground_set:
            tag.props.foreground = style.props.foreground

        if style.props.bold_set:
            tag.props.weight = pango.WEIGHT_BOLD if style.props.bold else pango.WEIGHT_NORMAL

    return tag
