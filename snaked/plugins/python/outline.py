import weakref
import re

from snaked.util import idle, join_to_file_dir, BuilderAware, refresh_gui
from snaked.core.shortcuts import ShortcutActivator

matcher = re.compile(r'(?m)^(?P<level>[ \t]*)(?P<type>def|class)\s+(?P<name>\w+)\s*\(')

def get_outline(source):
    last_start = 0
    last_line = 1
    cpath = (None,)
    cname = None
    clevel = None
    for match in matcher.finditer(source):
        last_line = last_line + source.count('\n', last_start, match.start())
        last_start = match.start()

        level, name = match.group('level', 'name')
        level = len(level)
        
        if clevel is None or level < clevel:
            cpath = cpath[:-1]
        elif level > clevel:
            cpath += (cname,)
        
        yield cpath, name, last_line
        
        clevel = level
        cname = name
            
class OutlineDialog(BuilderAware):
    def __init__(self):
        super(OutlineDialog, self).__init__(join_to_file_dir(__file__, 'outline.glade'))
        self.shortcuts = ShortcutActivator(self.window)
        self.shortcuts.bind('Escape', self.hide)
        self.shortcuts.bind('Return', self.goto_name)

    def show(self, editor):
        self.editor = weakref.ref(editor)
        self.search_entry.grab_focus()
        
        editor.request_transient_for.emit(self.window)
        self.window.present()
        
        idle(self.fill)

    def hide(self):
        self.window.hide()
        
    def on_delete_event(self, *args):
        self.hide()
        return True

    def goto_name(self):
        (model, iter) = self.outline_tree.get_selection().get_selected()
        self.hide()
        self.editor().goto_line(model.get_value(iter, 2))
        
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
        
        roots = (None, None)
        ptop = ()
        
        i = 0
        for top, name, line in get_outline(self.editor().text):
            if self.current_search is not current_search:
                return

            if len(top) == len(ptop):
                roots = roots[:-1] + (self.outline.append(roots[-2], (name, '', line)),)
            elif len(top) > len(ptop):
                roots = roots + (self.outline.append(roots[-1], (name, '', line)),)
            else:
                roots = roots[:-2] + (self.outline.append(roots[-3], (name, '', line)),)

            ptop = top
            
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
        
        outline = list(get_outline(self.editor().text))
        
        for m in (name_starts, name_contains):
            for top, name, line in outline:
                if self.current_search is not current_search:
                    return
                
                if (top, name) in already_matched: continue
                
                if m(name):
                    already_matched[(top, name)] = True            
                    self.outline.append(None, (name, u'/'.join(top), line))
                
                if i % 10 == 0:
                    refresh_gui()
                    
                i += 1

        self.outline_tree.columns_autosize()
