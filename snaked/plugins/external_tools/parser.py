import re

allowed_inputs = ('from-buffer-or-selection', 'from-buffer', 'from-selection')
allowed_outputs = ('replace-buffer-or-selection', 'replace-buffer', 'replace-selection',
    'to-console', 'to-iconsole', 'to-feedback', 'to-clipboard', 'insert', 'insert-at-end')

remove_tags = re.compile(r'<[^<]*?/?>')


class Tool(object):
    def __init__(self):
        self.context = None
        self.name = None
        self.input = None
        self.output = 'to-console'
        self.script = None

    @property
    def title(self):
        return remove_tags.sub('', self.name).strip().replace('_', '')


class ParseException(Exception): pass


class Context(object):
    def __init__(self):
        self.tools = []
        self.current_tool = None
        self.lineno = None
        self.script_lines = []

    def Error(self, msg):
        return ParseException('%d: %s' % (self.lineno, msg))

toolname_matcher = re.compile('tool\s+"(.*?)"')
for_matcher = re.compile('for\s+"(.*?)"')
input_matcher = re.compile('|'.join(allowed_inputs))
output_matcher = re.compile('|'.join(allowed_outputs))

def search_tool(ctx, line):
    if not line.startswith('tool'):
        return search_tool, True

    match = toolname_matcher.match(line)
    if not match:
        raise ctx.Error("Can't find tool name")

    line = toolname_matcher.sub('', line)

    tool = Tool()
    tool.name = match.group(1)

    ctx.tools.append(tool)
    ctx.current_tool = tool

    match = for_matcher.search(line)
    if match:
        tool.context = [s.strip() for s in match.group(1).split(',')]
        line = for_matcher.sub('', line)

    match = input_matcher.search(line)
    if match:
        tool.input = match.group(0)
        line = input_matcher.sub('', line)

    match = output_matcher.search(line)
    if match:
        tool.output = match.group(0)
        line = output_matcher.sub('', line)

    if line.strip():
        raise ctx.Error('Unexpected content: %s' % line.strip())

    ctx.script_lines[:] = []
    return consume_tool_script, True

def consume_tool_script(ctx, line):
    if line and not line[0].isspace():
        ctx.current_tool.script = '\n'.join(ctx.script_lines)
        return search_tool, False

    ctx.script_lines.append(line)
    return consume_tool_script, True

def parse(text):
    ctx = Context()
    func = search_tool
    for i, l in enumerate(text.splitlines()):
        ctx.lineno = i + 1
        while True:
            func, move_next = func(ctx, l)
            if move_next: break

    func(ctx, 'end')

    return ctx.tools