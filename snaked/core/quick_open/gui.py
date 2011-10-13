import os.path
import os
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
        self.shortcuts = Activator(self.window)
        self.shortcuts.bind('any', 'escape', '$_Close', self.escape)
        self.shortcuts.bind('any', 'activate-search-entry',
            'Activate search entry', self.focus_search)

        self.shortcuts.bind_accel('any', 'open-mime', 'Run _external editor',
            '<ctrl>Return', self.open_mime)
        self.shortcuts.bind_accel('any', 'open-dialog', '_Open...', '<ctrl>o', self.free_open)
        self.shortcuts.bind_accel('any', 'toggle-hidden', 'Toggle _hidden',
            '<ctrl>h', self.toggle_hidden)

        self.shortcuts.bind_accel('any', 'prev-project', '_Previous project', '<alt>Up', self.project_up)
        self.shortcuts.bind_accel('any', 'next-project', '_Next project', '<alt>Down', self.project_down)
        self.shortcuts.bind_accel('any', 'project-list', 'Show project _list',
            '<ctrl>p', self.popup_projects)
        self.shortcuts.bind_accel('any', 'delete-project', '_Delete project',
            '<ctrl>Delete', self.delete_project)
        self.shortcuts.bind_accel('any', 'goto-parent', 'Goto p_arent', 'BackSpace', self.browse_top)

        set_activate_the_one_item(self.search_entry, self.filelist_tree)

    def get_stored_recent_projects(self):
        return self.pwindow().manager.conf['QUICK_OPEN_RECENT_PROJECTS']

    def store_recent_projects(self, projects):
        self.pwindow().manager.conf['QUICK_OPEN_RECENT_PROJECTS'][:] = list(projects)

    def get_editor_project_root(self):
        editor = self.pwindow().get_editor_context()
        return editor.project_root if editor else None

    def show(self, window, on_dialog_escape=None):
        self.on_dialog_escape = on_dialog_escape
        self.pwindow = weakref.ref(window)
        self.update_recent_projects()

        editor = window.get_editor_context()
        if editor:
            self.update_projects(editor.get_project_root(larva=True))
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

    def update_projects(self, root):
        old_root = self.get_current_root()

        self.projects_cbox.handler_block_by_func(self.on_projects_cbox_changed)

        self.projects_cbox.set_model(None)
        self.projectlist.clear()

        index = 0
        for i, r in enumerate(settings.recent_projects):
            if r == root:
                index = i
            self.projectlist.append((r,))

        for i, r in enumerate(reversed(sorted(settings.larva_projects, key=lambda r:len(r)))):
            if r == root:
                index = i + len(settings.recent_projects)
            self.projectlist.append((r,))

        if not len(self.projectlist):
            self.projectlist.append((os.getcwd(),))

        self.projects_cbox.set_model(self.projectlist)
        self.projects_cbox.set_active(index)

        self.projects_cbox.handler_unblock_by_func(self.on_projects_cbox_changed)

        if self.get_current_root() != old_root:
            self.on_search_entry_changed()

    def hide(self):
        self.current_search = None
        self.window.hide()

    def on_delete_event(self, *args):
        self.escape()
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
        try:
            idx = self.projects_cbox.get_active()
            if idx >=0:
                return self.projectlist[idx][0]
        except IndexError:
            pass

        return None

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

        root = self.get_current_root()

        try:
            bad_re = settings.ignore_contexts[root]['ignore']
            def bad_matcher(path):
                return bad_re.search(path)

        except KeyError:
            bad_matcher = None

        for m in (searcher.name_start_match, searcher.name_match,
                searcher.path_match, searcher.fuzzy_match):
            for p in searcher.search(root, '', m(search), already_matched, bad_matcher, tick):
                if self.current_search is not current_search:
                    return

                already_matched[p] = True
                self.filelist.append(p)

                if len(self.filelist) > 150:
                    self.filelist_tree.columns_autosize()
                    return

        self.filelist_tree.columns_autosize()

    def fill_with_dirs(self, top='', place=False):
        self.filelist.clear()

        dirs = []
        files = []

        conf = self.pwindow().manager.conf
        hidden_masks = None
        if not conf['QUICK_OPEN_SHOW_HIDDEN']:
            hidden_masks = conf['QUICK_OPEN_HIDDEN_FILES']

        if top and not top.endswith('/'):
            top += '/'

        root = os.path.join(self.get_current_root(), top)
        for name in os.listdir(root):
            if hidden_masks and any(name.endswith(m) for m in hidden_masks):
                continue

            path = os.path.join(root, name)
            if os.path.isdir(path):
                dirs.append(name+'/')
            else:
                files.append(name)

        place_idx = 0
        for i, name in enumerate(sorted(dirs)):
            if name == place:
                place_idx = i
            self.filelist.append((name, top))

        for i, name in enumerate(sorted(files)):
            if name == place:
                place_idx = i + len(dirs)
            self.filelist.append((name, top))

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

    def on_projects_cbox_changed(self, *args):
        self.on_search_entry_changed()

    def get_selected_file(self):
        (model, iter) = self.filelist_tree.get_selection().get_selected()
        if iter:
            name, top = self.filelist.get(iter, 0, 1)
            return os.path.join(self.get_current_root(), top, name), name, top
        else:
            return None, None, None

    def open_file(self, *args):
        fname, name, top = self.get_selected_file()
        if fname:
            if os.path.isdir(fname):
                idle(self.fill_with_dirs, os.path.join(top, name), True)
            else:
                self.hide()
                refresh_gui()
                self.pwindow().open_or_activate(fname)

    def open_mime(self):
        fname, name, top = self.get_selected_file()
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
        dialog.set_current_folder(self.get_current_root())

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            idle(self.pwindow().open_or_activate, dialog.get_filename())
            idle(self.hide)

        dialog.destroy()

    def popup_projects(self):
        self.projects_cbox.popup()

    def delete_project(self):
        if len(self.projectlist):
            current_root = self.get_current_root()
            if current_root == self.get_editor_project_root():
                self.pwindow().emessage('You can not remove current project', 'warn')
                return

            settings.recent_projects.remove(current_root)
            self.store_recent_projects(settings.recent_projects)

            idx = self.projects_cbox.get_active()
            self.projectlist.remove(self.projects_cbox.get_active_iter())
            self.projects_cbox.set_active(idx % len(self.projectlist))
            self.pwindow().emessage('Project removed', 'done')

    def browse_top(self):
        if not self.filelist_tree.is_focus():
            return False

        if self.search_entry.get_text():
            self.pwindow().emessage('You are not in browse mode', 'warn')
            return

        fname, name, top = self.get_selected_file()
        if fname:
            if not top:
                self.pwindow().emessage('No way!', 'warn')
            else:
                place = os.path.basename(os.path.dirname(top)) + '/'
                idle(self.fill_with_dirs, os.path.dirname(os.path.dirname(top)), place)

    def toggle_hidden(self):
        if self.search_entry.get_text():
            self.pwindow().emessage('You are not in browse mode', 'warn')
            return

        conf = self.pwindow().manager.conf
        conf['QUICK_OPEN_SHOW_HIDDEN'] = not conf['QUICK_OPEN_SHOW_HIDDEN']

        self.pwindow().emessage('Show hidden files' if conf['QUICK_OPEN_SHOW_HIDDEN']
            else 'Do not show hidden files', 'info')

        fname, name, top = self.get_selected_file()
        if fname:
            idle(self.fill_with_dirs, top, name)
        else:
            if len(self.filelist):
                name, top = self.filelist[0]
                idle(self.fill_with_dirs, top)