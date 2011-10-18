import os.path
import weakref

import gtk
import gtksourceview2

from uxie.utils import idle, join_to_file_dir, join_to_settings_dir
from uxie.plugins import Manager as PluginManager
from uxie.actions import Activator, map_generic

from ..util import lazy_property, get_project_root, save_file

from . import prefs

from .editor import Editor
from .context import add_setter as add_context_setter, Processor as ContextProcessor

import snaked.core.quick_open
import snaked.core.titler
import snaked.core.editor_list
import snaked.core.window
import snaked.core.plugins
import snaked.core.console

prefs.add_option('RESTORE_POSITION', True, 'Restore snaked windows position')
prefs.add_option('CONSOLE_FONT', 'Monospace 8', 'Font used in console panel')
prefs.add_option('MIMIC_PANEL_COLORS_TO_EDITOR_THEME', True,
                 'Try to apply editor color theme to various panels')
prefs.add_option('WINDOW_BORDER_WIDTH', 0, 'Adjust window border width if you have bad wm')
prefs.add_option('SHOW_TABS', None,
                 'State of tabs visibility. Set it to None to use window specific settings')
prefs.add_option('TAB_BAR_PLACEMENT', None,
                 '''Tab bar placement position. One of "top", "bottom", "left", "right"
                    Set it to None to use window specific settings''')

prefs.add_internal_option('WINDOWS', list)
prefs.add_internal_option('MODIFIED_FILES', dict)

map_generic('root-menu', 'F1')
map_generic('activate-search-entry', '<ctrl>s')
map_generic('escape', 'Escape')
map_generic('delete', 'Delete')

map_generic('prev', '<ctrl>Up', 1)
map_generic('next', '<ctrl>Down', 1)

map_generic('goto-definition', 'F3')
map_generic('show-outline', '<ctrl>o')
map_generic('show-calltip', '<ctrl>Return')


class EditorManager(object):
    def __init__(self, session):
        self.buffers = []
        self.windows = []

        self.session = session
        self.style_manager = gtksourceview2.style_scheme_manager_get_default()
        self.lang_manager = gtksourceview2.language_manager_get_default()
        self.modify_lang_search_path(self.lang_manager)

        self.activator = Activator()
        self.activator.add_context('manager', (), lambda: self)
        self.activator.bind_accel('manager', 'quit', '_File/$_Quit', '<ctrl>q', EditorManager.quit)

        self.plugin_manager = PluginManager(self.activator)

        self.init_conf()

        self.escape_stack = []
        self.escape_map = {}
        self.spot_history = []
        self.context_processors = {}
        self.lang_contexts = {}
        self.ctx_contexts = {}
        self.on_quit = []

        # Init core plugins
        self.plugin_manager.add_plugin(snaked.core.quick_open)
        self.plugin_manager.add_plugin(snaked.core.editor_list)
        self.plugin_manager.add_plugin(snaked.core.titler)
        self.plugin_manager.add_plugin(snaked.core.console)

        add_context_setter('lang', self.set_lang_context)
        add_context_setter('ctx', self.set_ctx_context)

        self.plugin_manager.ready('manager', self)

        self.plugin_manager.add_plugin(snaked.core.window)

        snaked.core.plugins.init_plugins(self.plugin_manager)

    def init_conf(self):
        self.default_config = prefs.PySettings(prefs.options)
        self.default_config.load(prefs.get_settings_path('snaked.conf'))

        self.session_config = prefs.PySettings(parent=self.default_config)
        self.session_config.load(prefs.get_settings_path(self.session, 'config'))

        self.internal_config = prefs.PySettings(prefs.internal_options)
        self.internal_config.load(prefs.get_settings_path(self.session, 'internal'))

        self.conf = prefs.CompositePreferences(self.internal_config, self.session_config)

    def save_conf(self, active_editor=None):
        #self.snaked_conf['OPENED_FILES'] = [e.uri for e in self.editors if e.uri]
        #self.snaked_conf['ACTIVE_FILE'] = active_editor.uri if active_editor else None
        self.default_config.save()
        self.internal_config.save()
        self.session_config.save()

    def process_project_contexts(self, project_root, force=False):
        if project_root not in self.context_processors:
            contexts_filename = os.path.join(project_root, '.snaked_project', 'contexts')
            p = self.context_processors[project_root] = ContextProcessor(project_root, contexts_filename)
            p.process()
        else:
            if force:
                self.context_processors[project_root].process()

    def get_buffer_for_uri(self, filename):
        for buf in self.buffers:
            if buf.uri == filename:
                return buf

        return None

    def open(self, filename, line=None, contexts=None):
        buf = self.get_buffer_for_uri(filename)
        if buf:
            editor = Editor(self.conf, buf)
        else:
            editor = Editor(self.conf)
            self.buffers.append(editor.buffer)
            editor.buffer.session = self.session
            editor.buffer.uri = filename

            idle(self.set_buffer_prefs, editor.buffer, filename, contexts)
            idle(self.plugin_manager.ready, 'buffer-created', editor.buffer)
            idle(self.plugin_manager.ready, 'editor-with-new-buffer-created', editor)

            idle(editor.update_view_preferences)

            idle(editor.load_file, filename, line)
            idle(self.plugin_manager.ready, 'buffer-loaded', editor.buffer)

            idle(self.plugin_manager.ready, 'editor-with-new-buffer', editor)

        self.plugin_manager.ready('editor', editor)
        return editor

    def open_or_activate(self, uri, window=None):
        buf = self.get_buffer_for_uri(uri)
        if buf:
            if window:
                for e in window.editors:
                    if e.buffer is buf:
                        e.focus()
                        return e

            for e in self.get_editors():
                if e.buffer is buf:
                    e.focus()
                    return e
        else:
            window = window or [w for w in self.windows if w][0]
            e = self.open(uri)
            window.attach_editor(e)
            return e

    @lazy_property
    def lang_prefs(self):
        return prefs.load_json_settings('langs.conf', {})

    def set_buffer_prefs(self, buf, filename, lang_id=None):
        lang = None
        buf.lang = 'default'
        buf.contexts = [buf.lang]

        root = get_project_root(filename)
        if root:
            self.process_project_contexts(root)

        if not lang_id and root in self.lang_contexts:
            for id, matcher in self.lang_contexts[root].items():
                if matcher.search(filename):
                    lang_id = id
                    break

        if lang_id:
            lang = self.lang_manager.get_language(lang_id)
            if lang:
                buf.lang = lang.get_id()

        if not lang:
            lang = self.lang_manager.guess_language(filename, None)
            if lang:
                buf.lang = lang.get_id()

        buf.contexts = [buf.lang]

        if lang:
            buf.set_language(lang)

        if self.session:
            buf.contexts.append('session:' + self.session)

        if root in self.ctx_contexts:
            for ctx, matcher in self.ctx_contexts[root].items():
                if matcher.search(filename):
                    buf.contexts.append(ctx)

        buf.config = prefs.CompositePreferences(self.lang_prefs.get(buf.lang, {}),
            self.lang_prefs.get('default', {}), prefs.default_prefs.get(buf.lang, {}),
            prefs.default_prefs['default'])

        style_scheme = self.style_manager.get_scheme(buf.config['style'])
        buf.set_style_scheme(style_scheme)

    def on_request_to_open_file(self, editor, filename, line, lang_id):
        self.add_spot(editor)
        filename = os.path.normpath(filename)

        for e in self.editors:
            if e.uri == filename:
                self.focus_editor(e)

                if line is not None:
                    e.goto_line(line + 1)

                break
        else:
            e = self.open(filename, line, lang_id)

        return e

    @Editor.settings_changed(idle=True)
    def on_editor_settings_changed(self, editor):
        self.set_editor_prefs(editor, editor.uri, editor.lang)
        for e in self.editors:
            if e is not editor:
                idle(self.set_editor_prefs, e, e.uri, e.lang)

    def new_file_action(self, editor):
        from snaked.core.gui import new_file
        new_file.show_create_file(editor)

    def window_closed(self, window):
        self.windows[self.windows.index(window)] = False
        window.destroy()
        if not any(self.windows):
            self.quit()

    def get_editors(self):
        for w in self.windows:
            if w:
                for e in w.editors:
                    yield e

    def editor_closed(self, editor):
        buf = editor.buffer
        is_last_buffer = not any(e.buffer is buf for e in self.get_editors() if e is not editor)

        if is_last_buffer:
            self.plugin_manager.done('last-buffer-editor', editor)

        del editor.view
        del editor.buffer

        if not is_last_buffer:
            return

        self.plugin_manager.done('buffer', buf)

        self.buffers.remove(buf)
        if buf.get_modified():
            text = unicode(buf.get_text(*buf.get_bounds()), 'utf-8')
            self.conf['MODIFIED_FILES'][buf.uri] = save_file(buf.uri, text, buf.encoding, True)
        else:
            try:
                del self.conf['MODIFIED_FILES'][buf.uri]
            except KeyError:
                pass

    def quit(self):
        for w in self.windows:
            if w: w.close(False)

        self.save_conf()

        #self.plugin_manager.quit()

        for q in self.on_quit:
            try:
                q()
            except:
                import traceback
                traceback.print_exc()

        if gtk.main_level() > 0:
            gtk.main_quit()

    def show_key_preferences(self, editor):
        from snaked.core.gui.shortcuts import ShortcutsDialog
        dialog = ShortcutsDialog()
        dialog.show(editor)

    def show_preferences(self, editor):
        from snaked.core.gui.prefs import PreferencesDialog
        dialog = PreferencesDialog()
        dialog.show(editor)

    def show_editor_preferences(self, editor):
        from snaked.core.gui.editor_prefs import PreferencesDialog
        dialog = PreferencesDialog(self.lang_prefs)
        dialog.show(editor)

    def add_spot_with_feedback(self, editor):
        self.add_spot(editor)
        editor.message('Spot added')

    def add_spot(self, editor):
        self.add_spot_to_history(EditorSpot(self, editor))

    def add_spot_to_history(self, spot):
        self.spot_history = [s for s in self.spot_history
            if s.is_valid() and not s.similar_to(spot)]

        self.spot_history.insert(0, spot)

        while len(self.spot_history) > 30:
            self.spot_history.pop()

    def goto_last_spot(self, back_to=None):
        new_spot = EditorSpot(self, back_to) if back_to else None
        spot = self.get_last_spot(new_spot)
        if spot:
            spot.goto(back_to)
            if new_spot:
                self.add_spot_to_history(new_spot)
        else:
            if back_to:
                back_to.message('Spot history is empty')

    def get_last_spot(self, exclude_spot=None, exclude_editor=None):
        for s in self.spot_history:
            if s.is_valid() and not s.similar_to(exclude_spot) and s.editor() is not exclude_editor:
                return s

        return None

    def goto_next_prev_spot(self, editor, is_next):
        current_spot = EditorSpot(self, editor)
        if is_next:
            seq = self.spot_history
        else:
            seq = reversed(self.spot_history)

        prev_spot = None
        for s in (s for s in seq if s.is_valid()):
            if s.similar_to(current_spot):
                if prev_spot:
                    prev_spot.goto(editor)
                else:
                    editor.message('No more spots to go')
                return

            prev_spot = s

        self.goto_last_spot(editor)

    def show_global_preferences(self, editor):
        self.save_conf(editor)
        e = editor.open_file(join_to_settings_dir('snaked', 'snaked.conf'), lang_id='python')
        e.file_saved.connect(self, 'on_config_saved')

    def show_session_preferences(self, editor):
        self.save_conf(editor)
        e = editor.open_file(join_to_settings_dir('snaked', self.session + '.session'), lang_id='python')
        e.file_saved.connect(self, 'on_config_saved')

    def on_config_saved(self, editor):
        editor.message('Config updated')
        self.load_conf()

    def edit_contexts(self, editor):
        import shutil
        from os.path import join, exists, dirname
        from uxie.utils import make_missing_dirs

        contexts = join(editor.project_root, '.snaked_project', 'contexts')
        if not exists(contexts):
            make_missing_dirs(contexts)
            shutil.copy(join(dirname(__file__), 'contexts.template'), contexts)

        e = editor.open_file(contexts)
        e.file_saved.connect(self, 'on_context_saved')

    def on_context_saved(self, editor):
        editor.message('File type associations changed')
        self.process_project_contexts(editor.project_root, True)

    def modify_lang_search_path(self, manager):
        search_path = manager.get_search_path()
        user_path = os.path.expanduser('~')
        for i, p in enumerate(search_path):
            if not p.startswith(user_path):
                break

        search_path.insert(i, join_to_file_dir(__file__, 'lang-specs'))
        manager.set_search_path(search_path)

    def set_lang_context(self, project_root, contexts):
        self.lang_contexts[project_root] = contexts

    def set_ctx_context(self, project_root, contexts):
        self.ctx_contexts[project_root] = contexts

    def save_all(self, editor):
        for e in self.editors:
            e.save()

    def get_free_window(self):
        for idx, (w, wc) in enumerate(zip(self.windows, self.conf['WINDOWS'])):
            if not w:
                w = snaked.core.window.Window(self, wc)
                self.windows[idx] = w
                return w

        wc = {'name':'window%d' % len(self.windows)}
        self.conf['WINDOWS'].append(wc)
        w = snaked.core.window.Window(self, wc)
        self.windows.append(w)
        return w

    def start(self, files_to_open):
        opened_files = set()

        if not self.conf['WINDOWS']:
            self.conf['WINDOWS'].append({'name':'main'})

        main_window = None
        for window_conf in self.conf['WINDOWS']:
            files = [r['uri'] for r in window_conf.get('files', [])
                if os.path.exists(r['uri']) and os.path.isfile(r['uri'])]

            if files:
                w = snaked.core.window.Window(self, window_conf)
                self.windows.append(w)
                main_window = main_window or w

                for f in files:
                    e = self.open(f)
                    w.attach_editor(e)
                    opened_files.add(f)
            else:
                self.windows.append(False)

        window = main_window or self.get_free_window()
        for f in files_to_open:
            f = os.path.abspath(f)
            if f not in opened_files:
                e = self.open(f)
                window.attach_editor(e)
                opened_files.add(f)

        #if not manager.editors:
        #    import snaked.core.quick_open
        #    snaked.core.quick_open.quick_open(manager.get_fake_editor())
        #
        #if editor_to_focus and active_file != opened_files[-1]:
        #    manager.focus_editor(editor_to_focus)


class EditorSpot(object):
    def __init__(self, manager, editor):
        self.manager = manager
        self.editor = weakref.ref(editor)
        self.mark = editor.buffer.create_mark(None, editor.cursor)

    @property
    def iter(self):
        return self.mark.get_buffer().get_iter_at_mark(self.mark)

    def is_valid(self):
        return self.editor() and not self.mark.get_deleted()

    def similar_to(self, spot):
        return spot and self.mark.get_buffer() is spot.mark.get_buffer() \
            and abs(self.iter.get_line() - spot.iter.get_line()) < 7

    def __del__(self):
        buffer = self.mark.get_buffer()
        if buffer:
            buffer.delete_mark(self.mark)

    def goto(self, back_to=None):
        editor = self.editor()
        editor.buffer.place_cursor(self.iter)
        editor.scroll_to_cursor()

        if editor is not back_to:
            self.manager.focus_editor(editor)
