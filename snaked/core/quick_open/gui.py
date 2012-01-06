import os.path
import weakref

import gtk

from uxie.utils import idle, join_to_file_dir, refresh_gui
from uxie.misc import BuilderAware
from uxie.actions import Activator

from snaked.util import set_activate_the_one_item

import settings
import searcher

class QuickOpenDialog(BuilderAware):
    """glade-file: gui.glade"""

    def __init__(self):
        super(QuickOpenDialog, self).__init__(join_to_file_dir(__file__, 'gui.glade'))

        from snaked.core.manager import keymap
        self.shortcuts = keymap.get_activator(self.window, 'quick_open')
        self.shortcuts.bind('any', 'activate-search-entry',
            'Activate search entry', self.focus_search)

        self.shortcuts.bind('any', 'open-mime', 'Run _external editor',
            self.open_mime).to('<ctrl>Return')
        self.shortcuts.bind('any', 'open-dialog', '_Open...', self.free_open).to('<ctrl>o')
        self.shortcuts.bind('any', 'toggle-hidden', 'Toggle _hidden',
            self.toggle_hidden).to('<ctrl>h')

        self.shortcuts.bind('any', 'project-list', 'Toggle project _list',
            self.toggle_projects).to('<ctrl>p', 1)
        self.shortcuts.bind('projectlist', 'delete', '_Delete project', self.delete_project)
        self.shortcuts.bind('projectlist', 'set-root', 'Use as _root',
            self.use_as_root).to('Return', 1)

        self.shortcuts.bind('any', 'goto-parent', 'Goto p_arent', self.browse_top).to('BackSpace')
        self.shortcuts.bind('any', 'escape', '_Close', self.escape)

        self.shortcuts.add_context('projectlist', (),
            lambda: self.projectlist_tree if self.projectlist_tree.is_focus() else None)

        project_selection = self.projectlist_tree.get_selection()
        project_selection.set_mode(gtk.SELECTION_MULTIPLE)
        project_selection.connect_after('changed', self.on_projectlist_selection_changed)

        set_activate_the_one_item(self.search_entry, self.filelist_tree)

        self.roots = []

    def get_stored_recent_projects(self):
        return self.pwindow().manager.conf['QUICK_OPEN_RECENT_PROJECTS']

    def store_recent_projects(self, projects):
        self.pwindow().manager.conf['QUICK_OPEN_RECENT_PROJECTS'][:] = list(projects)

    def get_editor_project_root(self):
        editor = self.pwindow().get_editor_context()
        return editor.project_root if editor else None

    def get_selected_projects(self):
        cur_projects = self.pwindow().manager.conf['QUICK_OPEN_CURRENT_PROJECTS']
        if not cur_projects:
            editor = self.pwindow().get_editor_context()
            if editor:
                cur_projects = [editor.get_project_root(larva=True)]
            else:
                cur_projects = [os.getcwd()]

        return cur_projects

    def on_projectlist_selection_changed(self, selection):
        model, paths = selection.get_selected_rows()
        self.pwindow().manager.conf['QUICK_OPEN_CURRENT_PROJECTS'][:] = [model[r][1] for r in paths]
        self.update_projects(self.get_selected_projects())

    def use_as_root(self, pl):
        cursor, _ = pl.get_cursor()
        if cursor:
            self.update_projects([pl.get_model()[cursor][1]])
        else:
            self.pwindow().emessage('Which project?', 'warn')

    def show(self, window, on_dialog_escape=None):
        self.on_dialog_escape = on_dialog_escape
        self.pwindow = weakref.ref(window)
        self.update_recent_projects()

        editor = window.get_editor_context()
        if editor:
            self.update_projects(self.get_selected_projects())
        self.window.set_transient_for(window)

        self.search_entry.grab_focus()

        self.window.present()

    def update_recent_projects(self):
        saved_projects = self.get_stored_recent_projects()

        if any(p not in saved_projects for p in settings.recent_projects):
            [saved_projects.append(p) for p in settings.recent_projects
                if p not in saved_projects]
            self.store_recent_projects(saved_projects)
            settings.recent_projects = saved_projects
            return

        if any(p not in settings.recent_projects for p in saved_projects):
            [settings.recent_projects.append(p) for p in saved_projects
                if p not in settings.recent_projects]

        sel = self.projectlist_tree.get_selection()
        sel.handler_block_by_func(self.on_projectlist_selection_changed)
        self.projectlist_tree.set_model(None)
        self.projectlist.clear()

        cur_projects = self.pwindow().manager.conf['QUICK_OPEN_CURRENT_PROJECTS']

        toselect = []
        for i, r in enumerate(settings.recent_projects):
            it = self.projectlist.append((os.path.basename(r), r))
            if r in cur_projects:
                toselect.append(it)

        for i, r in enumerate(reversed(sorted(settings.larva_projects, key=lambda r:len(r)))):
            it = self.projectlist.append((os.path.basename(r), r))
            if r in cur_projects:
                toselect.append(it)

        self.projectlist_tree.set_model(self.projectlist)

        for it in toselect:
            self.projectlist_tree.get_selection().select_iter(it)

        sel.handler_unblock_by_func(self.on_projectlist_selection_changed)

    def update_projects(self, roots):
        self.projects_lb.set_text('\n'.join(roots))

        if self.roots != roots:
            self.on_search_entry_changed()

        self.roots[:] = roots

    def hide(self):
        self.current_search = None
        self.window.hide()

    def on_delete_event(self, *args):
        self.escape()
        return True

    def fill_filelist(self, search, current_search):
        self.filelist.clear()

        already_matched = {}
        counter = [-1]

        def tick():
            counter[0] += 1
            if counter[0] % 50 == 0:
                refresh_gui()
                if self.current_search is not current_search:
                    raise StopIteration()

        bad_matchers = {}
        for r in self.roots:
            try:
                bad_re = self.pwindow().manager.get_context_manager(r).get()['quick_open']['ignore']
            except KeyError:
                bad_matchers[r] = None
            else:
                bad_matchers[r] = lambda path, bre=bad_re: bre.search(path)

        for m in (searcher.name_start_match, searcher.name_match,
                searcher.path_match, searcher.fuzzy_match):
            for root in self.roots:
                for p in searcher.search(os.path.dirname(root), os.path.basename(root),
                        m(search), already_matched, bad_matchers[root], tick):
                    if self.current_search is not current_search:
                        return

                    already_matched[p] = True
                    self.filelist.append(p)

                    if len(self.filelist) > 150:
                        self.filelist_tree.columns_autosize()
                        return

        self.filelist_tree.columns_autosize()

    def fill_with_dirs(self, root='', top='', place=False):
        self.filelist.clear()

        dirs = []
        files = []

        conf = self.pwindow().manager.conf
        hidden_masks = None
        if not conf['QUICK_OPEN_SHOW_HIDDEN']:
            hidden_masks = conf['QUICK_OPEN_HIDDEN_FILES']

        if not top and len(self.roots) > 1:
            for r in self.roots:
                dirs.append((os.path.basename(r), r, os.path.dirname(r), ''))
        else:
            if not top:
                root = self.roots[0]

            for name in os.listdir(os.path.join(root, top)):
                if hidden_masks and any(name.endswith(m) for m in hidden_masks):
                    continue

                fpath = os.path.join(root, top, name)
                if os.path.isdir(fpath):
                    dirs.append((name, fpath, root, top))
                else:
                    files.append((name, fpath, root, top))

        place_idx = 0
        for i, (name, fpath, root, top) in enumerate(sorted(dirs) + sorted(files)):
            if name == place:
                place_idx = i
            self.filelist.append((name, top, fpath, root))
        self.filelist_tree.columns_autosize()

        if place and len(self.filelist):
            self.filelist_tree.set_cursor((place_idx,))

    def on_search_entry_changed(self, *args):
        search = self.search_entry.get_text().strip()
        self.current_search = object()
        if search:
            idle(self.fill_filelist, search, self.current_search)
        else:
            idle(self.fill_with_dirs)

    def get_selected_file(self):
        (model, iter) = self.filelist_tree.get_selection().get_selected()
        if iter:
            name, top, path, root = self.filelist.get(iter, 0, 1, 2, 3)
            return path, name, root, top
        else:
            return None, None, None, None

    def open_file(self, *args):
        fname, name, root, top = self.get_selected_file()
        if fname:
            if os.path.isdir(fname):
                idle(self.fill_with_dirs, root, os.path.join(top, name), True)
            else:
                self.hide()
                refresh_gui()
                self.pwindow().open_or_activate(fname)

    def open_mime(self):
        fname, name, root, top = self.get_selected_file()
        if fname:
            import gio
            self.hide()
            refresh_gui()

            f = gio.file_parse_name(fname)
            ct = f.query_info(gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE).get_content_type()
            ai = gio.app_info_get_default_for_type(ct, False)

            if ai:
                ai.launch([f])
            else:
                self.pwindow().emessage('Unknown content type for launch %s' % ct, 'error')

    def focus_search(self):
        self.search_entry.grab_focus()

    def escape(self):
        if self.on_dialog_escape:
            idle(self.on_dialog_escape, self)

        self.hide()

    def free_open(self):
        dialog = gtk.FileChooserDialog("Open file...",
            None,
            gtk.FILE_CHOOSER_ACTION_OPEN,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            gtk.STOCK_OPEN, gtk.RESPONSE_OK))

        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_current_folder(self.roots[0])

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            idle(self.pwindow().open_or_activate, dialog.get_filename())
            idle(self.hide)

        dialog.destroy()

    def toggle_projects(self):
        if not self.scrolledwindow2.get_visible():
            self.scrolledwindow2.show()

        if self.projectlist_tree.is_focus():
            self.scrolledwindow2.hide()
            self.window.resize(self.window.size_request()[0], self.window.get_size()[1])
            getattr(self, 'last_focus', self.search_entry).grab_focus()
        else:
            self.last_focus = self.window.get_focus()
            self.projectlist_tree.grab_focus()

    def delete_project(self, pl):
        if len(self.projectlist):
            cursor, _ = pl.get_cursor()
            if cursor:
                current_root = self.projectlist[cursor][1]
                if current_root in self.roots:
                    self.pwindow().emessage('You can not remove current project', 'warn')
                    return

                settings.recent_projects.remove(current_root)
                self.store_recent_projects(settings.recent_projects)

                self.projectlist.remove(self.projectlist[cursor].iter)
                self.pwindow().emessage('Project removed', 'done')

    def browse_top(self):
        if not self.filelist_tree.is_focus():
            return False

        if self.search_entry.get_text():
            self.pwindow().emessage('You are not in browse mode', 'warn')
            return

        fname, name, root, top = self.get_selected_file()
        if fname:
            if not top:
                self.pwindow().emessage('No way!', 'warn')
            else:
                place = os.path.basename(top)
                idle(self.fill_with_dirs, root, os.path.dirname(top), place)

    def toggle_hidden(self):
        if self.search_entry.get_text():
            self.pwindow().emessage('You are not in browse mode', 'warn')
            return

        conf = self.pwindow().manager.conf
        conf['QUICK_OPEN_SHOW_HIDDEN'] = not conf['QUICK_OPEN_SHOW_HIDDEN']

        self.pwindow().emessage('Show hidden files' if conf['QUICK_OPEN_SHOW_HIDDEN']
            else 'Do not show hidden files', 'info')

        fname, name, root, top = self.get_selected_file()
        if fname:
            idle(self.fill_with_dirs, root, top, name)
        else:
            if len(self.filelist):
                name, top = self.filelist[0]
                idle(self.fill_with_dirs, root, top)