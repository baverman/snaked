import os.path

import gtk
import gtksourceview2

from uxie.utils import idle, join_to_file_dir, join_to_settings_dir
from uxie.plugins import Manager as PluginManager
from uxie.actions import KeyMap

from ..util import lazy_property, get_project_root, save_file

from . import prefs

from .editor import Editor
from .context import Processor as ContextProcessor, Manager as ContextManager, \
                     FakeManager as FakeContextManager

import snaked.core.quick_open
import snaked.core.titler
import snaked.core.editor_list
import snaked.core.window
import snaked.core.plugins
import snaked.core.console
import snaked.core.spot
import snaked.core.monitor
import snaked.core.completer

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

keymap = KeyMap(join_to_settings_dir('snaked', 'keys.conf'))
keymap.map_generic('root-menu', 'F1')
keymap.map_generic('activate-search-entry', '<ctrl>s')
keymap.map_generic('escape', 'Escape')
keymap.map_generic('delete', 'Delete')

keymap.map_generic('prev', '<ctrl>Up', 1)
keymap.map_generic('next', '<ctrl>Down', 1)

keymap.map_generic('complete', '<ctrl>space', 1)
keymap.map_generic('goto-definition', 'F3')
keymap.map_generic('show-outline', '<ctrl>o')
keymap.map_generic('show-calltip', '<ctrl>Return', 1)

keymap.map_generic('run-test', '<ctrl>F10')
keymap.map_generic('run-all-tests', '<ctrl><shift>F10')
keymap.map_generic('rerun-test', '<shift><alt>x')
keymap.map_generic('toggle-test-panel', '<alt>1')


class EditorManager(object):
    def __init__(self, session):
        self.buffers = []
        self.windows = []

        self.session = session
        self.style_manager = gtksourceview2.style_scheme_manager_get_default()
        self.lang_manager = gtksourceview2.language_manager_get_default()
        self.modify_lang_search_path(self.lang_manager)

        self.activator = keymap.get_activator(config_section='editor_window')
        self.activator.add_context('manager', (), lambda: self)

        self.activator.bind_menu('_File#1')
        self.activator.bind_menu('_Edit#10')
        self.activator.bind_menu('_Prefs#15/_Global#90')
        self.activator.bind_menu('Prefs/_Session')
        self.activator.bind_menu('Prefs/_Project')
        self.activator.bind_menu('_View#20')
        self.activator.bind_menu('Too_ls#30')
        self.activator.bind_menu('_Run#40')
        self.activator.bind_menu('_Tab#90')
        self.activator.bind_menu('_Window#100')

        self.activator.bind('manager', 'quit', 'File/_Quit#100', EditorManager.quit).to('<ctrl>q')
        self.activator.bind('window', 'plugin-list', 'Prefs/Pl_ugins#10',
            snaked.core.plugins.show_plugins_prefs)

        self.activator.alias(('window', 'activator'), 'root-menu', 'Prefs/_Root menu#100')

        self.plugin_manager = PluginManager(self.activator)

        self.init_conf()

        self.default_ctx_processor = ContextProcessor(join_to_settings_dir('snaked', 'contexts.conf'))
        self.session_ctx_processor = ContextProcessor(
            join_to_settings_dir('snaked', self.session, 'contexts'))
        self.ctx_managers = {}

        self.escape_stack = []
        self.escape_map = {}
        self.on_quit = []

        # Init core plugins
        self.plugin_manager.add_plugin(prefs)
        self.plugin_manager.add_plugin(snaked.core.quick_open)
        self.plugin_manager.add_plugin(snaked.core.editor_list)
        self.plugin_manager.add_plugin(snaked.core.titler)
        self.plugin_manager.add_plugin(snaked.core.console)
        self.plugin_manager.add_plugin(snaked.core.spot)
        self.plugin_manager.add_plugin(snaked.core.monitor)
        self.plugin_manager.add_plugin(snaked.core.completer)

        self.spot_manager = snaked.core.spot.Manager()

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
        self.default_config.save()
        self.internal_config.save()
        self.session_config.save()

    def get_context_manager(self, project_root):
        try:
            return self.ctx_managers[project_root]
        except KeyError:
            pass

        if project_root:
            manager = ContextManager(project_root,
                [self.default_ctx_processor, self.session_ctx_processor],
                os.path.join(project_root, '.snaked_project', 'contexts'))
        else:
            manager = FakeContextManager()

        self.ctx_managers[project_root] = manager
        return manager

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

        idle(self.plugin_manager.ready, 'editor', editor)
        return editor

    def open_or_activate(self, uri, window=None, line=None):
        buf = self.get_buffer_for_uri(uri)
        if buf:
            if window:
                for e in window.editors:
                    if e.buffer is buf:
                        if line is not None:
                            e.goto_line(line)
                        e.focus()
                        return e

            for e in self.get_editors():
                if e.buffer is buf:
                    if line is not None:
                        e.goto_line(line)
                    e.focus()
                    return e
        else:
            window = window or [w for w in self.windows if w][0]
            e = self.open(uri, line)
            window.attach_editor(e)
            return e

    @lazy_property
    def lang_prefs(self):
        return prefs.load_json_settings('langs.conf', {})

    def set_buffer_prefs(self, buf, filename, lang_id=None):
        lang = None
        buf.lang = 'default'

        root = get_project_root(filename)
        ctx_manager = self.get_context_manager(root)

        if not lang_id:
            lang_id = ctx_manager.get_first('lang', filename)

        if lang_id:
            lang = self.lang_manager.get_language(lang_id)
            if lang:
                buf.lang = lang.get_id()

        if not lang:
            lang = self.lang_manager.guess_language(filename, None)
            if lang:
                buf.lang = lang.get_id()

        if lang:
            buf.set_language(lang)

        buf.contexts = [buf.lang]
        buf.contexts += ctx_manager.get_all('ctx', filename)

        if self.session:
            buf.contexts.append('session:' + self.session)

        buf.config = prefs.CompositePreferences(self.lang_prefs.get(buf.lang, {}),
            self.lang_prefs.get('default', {}), prefs.default_prefs.get(buf.lang, {}),
            prefs.default_prefs['default'])

        style_scheme = self.style_manager.get_scheme(buf.config['style'])
        buf.set_style_scheme(style_scheme)

    def window_closed(self, window):
        self.windows[self.windows.index(window)] = False
        window.destroy()
        if not any(self.windows):
            self.quit()

    def get_editors(self):
        for w in self.get_windows():
            for e in w.editors:
                yield e

    def get_windows(self):
        for w in self.windows:
            if w:
                yield w

    def editor_closed(self, editor):
        buf = editor.buffer
        is_last_buffer = not any(e.buffer is buf for e in self.get_editors() if e is not editor)

        self.plugin_manager.done('editor', editor)

        if is_last_buffer:
            self.plugin_manager.done('last-buffer-editor', editor)

        editor.on_close()
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

        self.plugin_manager.done('manager', self)

        for q in self.on_quit:
            try:
                q()
            except:
                import traceback
                traceback.print_exc()

        if gtk.main_level() > 0:
            gtk.main_quit()

    def modify_lang_search_path(self, manager):
        search_path = manager.get_search_path()
        user_path = os.path.expanduser('~')
        for i, p in enumerate(search_path):
            if not p.startswith(user_path):
                break

        search_path.insert(i, join_to_file_dir(__file__, 'lang-specs'))
        manager.set_search_path(search_path)

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
            window.window_conf['active-uri'] = f
            if f not in opened_files:
                e = self.open(f)
                window.attach_editor(e)
                opened_files.add(f)

        for w in self.windows:
            if w:
                if w.window_conf.get('active-uri', None):
                    w.open_or_activate(w.window_conf['active-uri'])

        if not self.buffers:
            snaked.core.quick_open.quick_open(window)

