import re

class Snippet(object):
    def __init__(self, snippet, variant):
        self.snippet = snippet
        self.variant = variant
        self.comment = ''
        self.body = []

        if variant:
            self.label = snippet + ' ' + variant
        else:
            self.label = snippet

    def get_body_and_offsets(self, indent=u'', expand_tabs=False, tab_width=4):
        tab_offsets = {}
        insert_offsets = {}
        replaces = {}
        matcher = re.compile(ur'\$\{(\d+)(:(.*?))?\}')

        body = (u'\n' + indent).join(
            s.expandtabs(tab_width) if expand_tabs else s for s in self.body)

        for m in matcher.finditer(body):
            if m.group(3):
                replaces[int(m.group(1))] = m.group(3)

        delta = [0]
        def replace_stops(match):
            idx = int(match.group(1))
            replace = replaces.get(idx, u'')

            start = delta[0] + match.start()
            delta[0] += len(replace) - match.end() + match.start()
            end = delta[0] + match.end()

            tab_offsets[idx] = start, end

            return replace

        def replace_inserts(match):
            idx = int(match.group(1))
            replace = replaces.get(idx, u'')

            start = delta[0] + match.start()
            dt = len(replace) - match.end() + match.start()
            delta[0] += dt
            end = delta[0] + match.end()

            for k, (s, e) in tab_offsets.iteritems():
                if s >= start: s += dt
                if e >= start: e += dt
                tab_offsets[k] = s, e

            insert_offsets.setdefault(idx, []).append((start, end))

            return replace

        body = matcher.sub(replace_stops, body)
        delta[0] = 0
        body = re.sub(ur'\$(\d+)', replace_inserts, body)

        return body, tab_offsets, insert_offsets


def parse_snippets_from(filename):
    pl = ''
    csnippet = None
    snippets = {}
    for l in open(filename).read().decode('utf-8').splitlines():
        if l.startswith('snippet'):
            tag_and_variant = l.split(None, 2)[1:]
            if len(tag_and_variant) == 2:
                tag, variant = tag_and_variant
            else:
                tag, variant = tag_and_variant[0], None
            csnippet = Snippet(tag, variant)
            snippets[csnippet.label] = csnippet
            if pl.startswith('#'):
                csnippet.comment = pl[1:].strip()
        elif l.startswith('\t') and csnippet:
            csnippet.body.append(l[1:])

        pl = l

    return snippets