import pango
import glib

brackets = {
    '(': (')', 1),
    ')': ('(', -1),
    '[': (']', 1),
    ']': ('[', -1),
    '{': ('}', 1),
    '}': ('{', -1),
}

matched_tags = [None]
cursor_movement_occurs = [False]
highlight_timer_id = [None]

def match_brackets_timeout(buf):
    if not cursor_movement_occurs[0]:
        highlight_matching_brackets(buf)
        highlight_timer_id[0] = None
        return False

    cursor_movement_occurs[0] = False
    return True

def add_highlight_task(buf):
    if not highlight_timer_id[0]:
        cursor_movement_occurs[0] = True
        highlight_timer_id[0] = glib.timeout_add(100, match_brackets_timeout, buf)
    else:
        cursor_movement_occurs[0] = True

def attach(editor):
    editor.buffer.set_highlight_matching_brackets(False)
    editor.buffer.connect_after('notify', on_buffer_notify)

def reset_tags(buf):
    if matched_tags[0] and buf.get_tag_table().lookup(matched_tags[0]):
        start, end = buf.get_bounds()
        buf.remove_tag_by_name(matched_tags[0], start, end)
        matched_tags[0] = None

def highlight_matching_brackets(buf):
    """:type buf: gtk.TextBuffer()"""
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

def on_buffer_notify(buf, prop):
    if prop.name == 'cursor-position':
        add_highlight_task(buf)

def find_bracket(from_iter, br, obr, dir):
    iter = from_iter.copy()
    depth = 1
    while True:
        if not iter.forward_cursor_positions(dir):
            break

        c = iter.get_char()
        if c == br:
            depth -= 1
        elif c == obr:
            depth += 1

        if depth == 0:
            return iter

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

def get_tag(buf, type, fallback='bracket-match'):
    table = buf.get_tag_table()
    tag = table.lookup(type)
    if not tag:
        style = buf.get_style_scheme().get_style(type)
        if not style:
            style = buf.get_style_scheme().get_style(fallback)

        tag = buf.create_tag(type)

        if style.props.background_set:
            tag.props.background = style.props.background

        if style.props.foreground_set:
            tag.props.foreground = style.props.foreground

        if style.props.bold_set:
            tag.props.weight = pango.WEIGHT_BOLD if style.props.bold else pango.WEIGHT_NORMAL

    return tag
