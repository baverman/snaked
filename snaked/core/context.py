import os.path
import re

setters = {}

def add_setter(ctx, callback):
    setters[ctx] = callback

class Processor(object):
    def __init__(self, root, filename):
        self.root = root
        self.filename = filename

    def process(self):
        result = {}

        try:
            for l in open(self.filename):
                l = l.strip()
                if not l or l.startswith('#'):
                    continue

                try:
                    expr, contexts = l.split(':', 1)
                except ValueError:
                    continue

                contexts = [c.strip() for c in contexts.split(',')]
                if not contexts:
                    continue

                if not l.startswith('/'):
                    expr = '/*/' + expr

                expr = self.root + re.escape(expr).replace('\*', '.*') + '$'

                for c in contexts:
                    try:
                        ctx, param = c.split(':', 1)
                    except ValueError:
                        print 'Bad context:', c
                        continue

                    result.setdefault(ctx, {}).setdefault(param, []).append(expr)
        except IOError:
            pass

        for params in result.values():
            for param in params:
                params[param] = re.compile('|'.join(params[param]))

        self.send_contexts(result)

    def send_contexts(self, contexts):
        for ctx, callback in setters.items():
            callback(self.root, contexts.get(ctx, {}))

        unknown_contexts = [c for c in contexts if c not in setters]
        if unknown_contexts:
            print "I don't know how to handle", unknown_contexts, "contexts"