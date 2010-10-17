import os.path
import weakref

from snaked.util import idle, join_to_file_dir, BuilderAware, open_mime, refresh_gui, single_ref
from snaked.core.shortcuts import ShortcutActivator
from snaked.core.prefs import ListSettings

import settings
import searcher

class QuickOpenDialog(BuilderAware):
    def __init__(self):
        super(QuickOpenDialog, self).__init__(join_to_file_dir(__file__, 'gui.glade'))
        self.shortcuts = ShortcutActivator(self.window)
        self.shortcuts.bind('Escape', self.hide)
        self.shortcuts.bind('<alt>Up', self.project_up)
        self.shortcuts.bind('<alt>Down', self.project_down)
        self.shortcuts.bind('Return', self.open_file)
        self.shortcuts.bind('<ctrl>Return', self.open_mime)
        self.shortcuts.bind('<alt>s', self.focus_search)

    @single_ref
    def prefs(self):
        return ListSettings('project-roots.db')
        
    def show(self, editor):
        self.editor = weakref.ref(editor)
        
        self.update_recent_projects()
        self.update_projects(editor.project_root)

        self.search_entry.grab_focus()
        
        editor.request_transient_for.emit(self.window)
        self.window.present()
    
    def update_recent_projects(self):
        saved_projects = self.prefs.load()
                
        if any(p not in saved_projects for p in settings.recent_projects):
            [saved_projects.append(p) for p in settings.recent_projects
                if p not in saved_projects]
            self.prefs.store(saved_projects)
            settings.recent_projects = saved_projects
            return
            
        if any(p not in settings.recent_projects for p in saved_projects):
            [settings.recent_projects.append(p) for p in saved_projects
                if p not in settings.recent_projects]
    
    def update_projects(self, root):
        self.projects_cbox.set_model(None)
        self.projectlist.clear()
        
        index = 0
        for i, r in enumerate(settings.recent_projects):
            if r == root:
                index = i
            self.projectlist.append((r,))
        
        self.projects_cbox.set_model(self.projectlist)
        self.projects_cbox.set_active(index)
    
    def hide(self):
        self.window.hide()
        
    def on_delete_event(self, *args):
        self.hide()
        return True
    
    def project_up(self):
        idx = self.projects_cbox.get_active()
        idx = ( idx - 1 ) % len(self.projectlist)
        self.projects_cbox.set_active(idx)
        
    def project_down(self):
        idx = self.projects_cbox.get_active()
        idx = ( idx + 1 ) % len(self.projectlist)
        self.projects_cbox.set_active(idx)

    def get_current_root(self):
        return self.projectlist[self.projects_cbox.get_active()][0]
    
    def fill_filelist(self, search):
        self.filelist.clear()
        
        current_search = object()
        self.current_search = current_search
        
        already_matched = {}
        i = 0
        
        for m in (searcher.name_start_match, searcher.name_match,
                searcher.path_match, searcher.fuzzy_match):
            for p in searcher.search(self.get_current_root(), '', m(search), already_matched):
                if self.current_search is not current_search:
                    return
                    
                already_matched[p] = True            
                self.filelist.append(p)
                
                if i % 10 == 0:
                    refresh_gui()
                    
                i += 1

        self.filelist_tree.columns_autosize()

    def on_search_entry_changed(self, *args):
        search = self.search_entry.get_text().strip()
        if search:
            idle(self.fill_filelist, search)
        
    def on_projects_cbox_changed(self, *args):
        self.on_search_entry_changed()

    def get_selected_file(self):
        (model, iter) = self.filelist_tree.get_selection().get_selected()
        if iter:
            return os.path.join(self.get_current_root(), *self.filelist.get(iter, 1, 0))
        else:
            return None
    
    def open_file(self):
        fname = self.get_selected_file()
        if fname:
            self.hide()
            refresh_gui()
            self.editor().open_file(fname)
        
    def open_mime(self):
        fname = self.get_selected_file()
        if fname:
            self.hide()
            refresh_gui()
            open_mime(fname)

    def focus_search(self):
        self.search_entry.grab_focus()