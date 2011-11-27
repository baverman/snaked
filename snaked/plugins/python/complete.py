import textwrap

import weakref
from glib import markup_escape_text

from snaked.core.completer import Provider


def pangonify_rst(text):
    result = ''

    lines = text.strip().expandtabs().splitlines()

    if len(lines) > 1 and lines[1].strip():
        lines = [lines[0]] + [''] + lines[1:]

    indent = 1000
    for l in lines[1:]:
        stripped = l.lstrip()
        if stripped:
            indent = min(indent, len(l) - len(stripped))

    trimmed = [lines[0].strip()]
    if indent < 1000:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())

    wrapper = textwrap.TextWrapper(width=60)
    paragraph = ''
    break_paragraph = False

    def add_paragraph():
        r = result
        if paragraph:
            if break_paragraph:
                r += '\n'

            r += wrapper.fill(paragraph) + '\n\n'
            return r, '', False

        return r, '', break_paragraph

    for l in trimmed:
        if not l.strip():
            result, paragraph, break_paragraph = add_paragraph()
        else:
            if l.startswith('  '):
                result, paragraph, break_paragraph = add_paragraph()
                break_paragraph = True
                result += "<tt>%s</tt>" % markup_escape_text(l)
                result += '\n'
            else:
                paragraph += markup_escape_text(l) + ' '

    if paragraph:
        result, _, _ = add_paragraph()

    return result


class RopeCompletionProvider(Provider):
    def __init__(self, plugin):
        self.plugin = weakref.ref(plugin)

    def get_name(self):
        return 'python'

    def is_match(self, it):
        return it

    def complete(self, it, is_interactive):
        env = self.plugin().env
        root = self.plugin().project_path
        try:
            source, offset = self.plugin().get_source_and_offset()
            match, proposals = env.assist(root, source, offset, self.plugin().editor.uri)
        except Exception, e:
            import traceback
            traceback.print_exc()
            self.plugin().editor.message(str(e), 'error', 5000)
            return

        if proposals:
            for r in proposals:
                yield r, (r, match)
        else:
            self.plugin().editor.message("Can't assist")
            return

    def activate(self, textview, (proposal, match)):
        buf = textview.get_buffer()

        buf.begin_user_action()
        cursor = buf.get_iter_at_mark(buf.get_insert())
        start = cursor.copy()
        start.backward_chars(len(match))
        buf.delete(start, cursor)
        buf.insert_at_cursor(proposal)
        buf.end_user_action()
