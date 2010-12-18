import re

match_start = re.compile(r'"""|\'\'\'|"|\'|\(|\[|\{|\)|\]|\}')
match_quote_end = {
    '"""': re.compile(r'.*?"""'),
    "'''": re.compile(r".*?'''"),
    "'": re.compile(r"'|.*?[^\\]'"),
    '"': re.compile(r'"|.*?[^\\]"'),
}

inverted = {
    ')': '(',
    '}': '{',
    ']': '[',
}

def find_closing_quote_pos(quote, text, start):
    m = match_quote_end[quote].match(text, start)
    if m:
        return m.end()

    return None

def get_brackets(text, cursor):
    start = 0
    open = []
    close = []
    level = None
    while True:
        m = match_start.search(text, start)
        if not m:
            break

        start = m.end()
        bracket = m.group()

        if start > cursor:
            if not open:
                return None, None, None
            elif level is None:
                level = len(open) - 1

        if bracket in ['"""', "'''", '"', "'"]:
            end = find_closing_quote_pos(bracket, text, start)
            if not end:
                return None, None, None
            if level is None and end > cursor:
                return bracket, start, end
            else:
                start = end
        elif bracket in ['(', '[', '{']:
            open.append((bracket, start))
        elif open and bracket in [')', ']', '}']:
            close.append((inverted[bracket], start))

        #print open, close, text, text[4]
        while open and close and open[-1][0] == close[-1][0]:
            br, opos = open.pop()
            br, cpos = close.pop()

            if len(open) == level:
                return br, opos, cpos

    return None, None, None