import weakref
import ast
import re

from uxie.utils import idle, join_to_file_dir, refresh_gui
from uxie.misc import BuilderAware

from snaked.util import set_activate_the_one_item

match_ws = re.compile('^[ \t]+')
def get_ws_len(line):
    match = match_ws.search(line)
    if match:
        return len(match.group(0))
    else:
        return 0

def parse_bad_code(code, tries=4):
    try:
        return ast.parse(code)
    except IndentationError, e:
        if not tries:
            raise

        code = code.splitlines()
        result = []
        for i, l in reversed(list(enumerate(code[:e.lineno-1]))):
            if l.strip():
                result.extend(code[:i])
                result.append(l + ' pass')
                result.extend(code[i+1:])
                break

        return parse_bad_code('\n'.join(result), tries-1)

    except SyntaxError, e:
        if not tries:
            raise

        code = code.splitlines()
        level = get_ws_len(code[e.lineno - 1])
        result = code[:e.lineno-1]
        result.append('')
        for i, l in enumerate(code[e.lineno:], e.lineno):
            if l.strip() and get_ws_len(l) <= level:
                result.extend(code[i:])
                break
            else:
                result.append('')

        return parse_bad_code('\n'.join(result), tries-1)


class OutlineVisitor(ast.NodeVisitor):
    def __init__(self):
        self.parent = ()
        self.nodes = []

    def process_childs(self,node):
        self.parent += (node.name,)
        self.generic_visit(node)
        self.parent = self.parent[:-1]

    def visit_ClassDef(self, node):
        self.nodes.append((self.parent, node))
        self.process_childs(node)

    def visit_FunctionDef(self, node):
        self.nodes.append((self.parent, node))
        self.process_childs(node)


class OutlineDialog(BuilderAware):
    def __init__(self):
        super(OutlineDialog, self).__init__(join_to_file_dir(__file__, 'outline.glade'))

        from snaked.core.manager import keymap
        self.activator = keymap.get_activator(self.window)
        self.activator.bind('any', 'escape', None, self.hide)
        self.activator.bind('any', 'activate-search-entry', None, self.focus_search)

        set_activate_the_one_item(self.search_entry, self.outline_tree)

    def show(self, editor):
        self.tree = None
        self.editor = weakref.ref(editor)
        self.search_entry.grab_focus()

        self.window.set_transient_for(editor.window)
        self.window.present()

        idle(self.fill)

    def get_tree(self):
        if not self.tree:
            visitor = OutlineVisitor()
            try:
                tree = parse_bad_code(self.editor().text)
                visitor.visit(tree)
                self.tree = visitor.nodes
            except (SyntaxError, IndentationError), e:
                print e
                self.tree = []

        return self.tree

    def hide(self):
        self.window.hide()

    def on_delete_event(self, *args):
        self.hide()
        return True

    def goto_name(self, *args):
        (model, iter) = self.outline_tree.get_selection().get_selected()
        if iter:
            self.hide()
            self.editor().add_spot()
            self.editor().goto_line(model.get_value(iter, 2))
        else:
            self.editor().message('You need select item', 'warn')

    def on_search_entry_changed(self, *args):
        what = self.search_entry.get_text().strip()
        if what:
            idle(self.filter, what)
        else:
            idle(self.fill)

    def fill(self):
        self.outline.clear()
        current_search = object()
        self.current_search = current_search

        roots = {():None}

        i = 0
        for parent, node in self.get_tree():
            if self.current_search is not current_search:
                return

            roots[parent + (node.name,)] = self.outline.append(roots[parent],
                (node.name, '', node.lineno))

            if i % 10 == 0:
                self.outline_tree.expand_all()
                self.outline_tree.columns_autosize()
                refresh_gui()

            i += 1

        self.outline_tree.expand_all()
        self.outline_tree.columns_autosize()

    def filter(self, search):
        self.outline.clear()

        current_search = object()
        self.current_search = current_search

        already_matched = {}
        i = 0

        def name_starts(name):
            return name.startswith(search)

        def name_contains(name):
            return search in name

        outline = self.get_tree()

        for m in (name_starts, name_contains):
            for top, node in outline:
                if self.current_search is not current_search:
                    return

                name, line = node.name, node.lineno

                if (top, name) in already_matched: continue

                if m(name):
                    already_matched[(top, name)] = True
                    self.outline.append(None, (name, u'/'.join(top), line))

                if i % 10 == 0:
                    refresh_gui()

                i += 1

        self.outline_tree.columns_autosize()

    def focus_search(self):
        self.search_entry.grab_focus()