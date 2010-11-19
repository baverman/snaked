import re

def remove_trailing_spaces(buffer):
    matcher = re.compile(r'(?um)([ \t]+)$')
    while True:
        match = matcher.search(buffer.get_text(*buffer.get_bounds()).decode('utf-8'))
        if match:
            buffer.delete(*map(buffer.get_iter_at_offset, match.span(1)))
        else:
            break
