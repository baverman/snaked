import os.path
import re

class Manager(object):
    def __init__(self, project_root, parent_processors, project_context_config):
        self.root = project_root
        self.processors = list(parent_processors)
        self.project_processor = Processor(project_context_config)
        self.processors.append(self.project_processor)

    def invalidate(self):
        try:
            del self.contexts
        except AttributeError:
            pass

        for p in self.processors:
            p.invalidate()

    def get(self):
        try:
            return self.contexts
        except AttributeError:
            pass

        rules = {}
        for p in self.processors:
            for ctx, params in p.get_rules().iteritems():
                for p, expr_list in params.iteritems():
                    pe = rules.setdefault(ctx, {}).setdefault(p, [])
                    pe += expr_list

        result = self.contexts = {}
        root = re.escape(self.root)
        for ctx, params in rules.iteritems():
            for param, expr_list in params.iteritems():
                result.setdefault(ctx, {})[param] = re.compile(
                    '|'.join(root + r for r in expr_list))

        return result

    def get_first(self, ctx, uri):
        for p, matcher in self.get().get(ctx, {}).iteritems():
            if matcher.match(uri):
                return p

        return None

    def get_all(self, ctx, uri):
        result = []
        for p, matcher in self.get().get(ctx, {}).iteritems():
            if matcher.match(uri):
                result.append(p)

        return result


class FakeManager(Manager):
    def __init__(self):
        self.contexts = {}

    def invalidate(self):
        pass

    def get(self):
        return self.contexts


class Processor(object):
    def __init__(self, filename):
        self.filename = filename

    def get_rules(self):
        try:
            return self.rules
        except AttributeError:
            pass

        self.rules = {}
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

                expr = re.escape(expr).replace('\*', '.*') + '$'

                for c in contexts:
                    try:
                        ctx, param = c.split(':', 1)
                    except ValueError:
                        print 'Bad context:', c
                        continue

                    self.rules.setdefault(ctx, {}).setdefault(param, []).append(expr)
        except IOError:
            pass

        return self.rules

    def invalidate(self):
        try:
            del self.rules
        except AttributeError:
            pass
