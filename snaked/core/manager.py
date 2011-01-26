import os.path
import weakref

import gtk
import gtksourceview2
import pango

from ..signals import connect_all
from ..util import (idle, lazy_property, get_project_root, join_to_file_dir, join_to_settings_dir)

from . import prefs
from snaked.core import config

from .shortcuts import register_shortcut, load_shortcuts
from .plugins import PluginManager
from .editor import Editor
from .context import add_setter as add_context_setter, Processor as ContextProcessor

import snaked.core.quick_open
import snaked.core.titler
import snaked.core.editor_list

class EditorManager(object):
    def __init__(self, session):
        self.editors = []
        self.session = session
        self.style_manager = gtksourceview2.style_scheme_manager_get_default()
        self.lang_manager = gtksourceview2.language_manager_get_default()
        self.modify_lang_search_path(self.lang_manager)

        self.on_quit = []

        self.plugin_manager = PluginManager()
        prefs.register_dialog('Plugins', self.plugin_manager.show_plugins_prefs, 'plugin',
            'extension')

        prefs.register_dialog('Key configuration', self.show_key_preferences, 'key', 'bind', 'shortcut')

        prefs.register_dialog('Editor settings', self.show_editor_preferences,
            'editor', 'font', 'style', 'margin', 'line', 'tab', 'whitespace')

        prefs.register_dialog('Global preferences', self.show_global_preferences,
            'snaked', 'global', 'preferences')

        prefs.register_dialog('Session preferences', self.show_session_preferences,
            'session', 'preferences')

        prefs.register_dialog('File types', self.edit_contexts, 'file', 'type', 'association')

        self.snaked_conf = config.SnakedConf()
        self.load_conf()

        self.escape_stack = []
        self.escape_map = {}
        self.spot_history = []
        self.context_processors = {}
        self.lang_contexts = {}
        self.ctx_contexts = {}

        load_shortcuts()
        self.register_app_shortcuts()

        # Init core plugins
        self.plugin_manager.load_core_plugin(snaked.core.quick_open)
        self.plugin_manager.load_core_plugin(snaked.core.titler)
        self.plugin_manager.load_core_plugin(snaked.core.editor_list)

        add_context_setter('lang', self.set_lang_context)
        add_context_setter('ctx', self.set_ctx_context)

    def load_conf(self):
        self.snaked_conf.clear()

        self.snaked_conf.load('snaked.conf')
        if self.session:
            self.snaked_conf.load(self.session + '.session')

    def save_conf(self, active_editor=None):
        self.snaked_conf['OPENED_FILES'] = [e.uri for e in self.editors if e.uri]
        self.snaked_conf['ACTIVE_FILE'] = active_editor.uri if active_editor else None
        self.snaked_conf.save()

    def register_app_shortcuts(self):
        register_shortcut('quit', '<ctrl>q', 'Application', 'Quit')
        register_shortcut('close-window', '<ctrl>w', 'Window', 'Close window')
        register_shortcut('save', '<ctrl>s', 'File', 'Save file')
        register_shortcut('save-all', '<ctrl><shift>s', 'File', 'Save all opened files')
        register_shortcut('new-file', '<ctrl>n', 'File',
            'Open dialog to choose new file directory and name')
        register_shortcut('show-preferences', '<ctrl>p', 'Window', 'Open preferences dialog')

        register_shortcut('place-spot', '<alt>t', 'Edit', 'Place spot at current cursor location')
        register_shortcut('goto-last-spot', '<alt>q', 'Edit', 'Quick jump to last placed spot')
        register_shortcut('goto-next-spot', '<ctrl><alt>Right', 'Edit',
            'Quick jump to next spot in history')
        register_shortcut('goto-prev-spot', '<ctrl><alt>Left', 'Edit',
            'Quick jump to previous spot in history')

    def process_project_contexts(self, project_root, force=False):
        if project_root not in self.context_processors:
            contexts_filename = os.path.join(project_root, '.snaked_project', 'contexts')
            p = self.context_processors[project_root] = ContextProcessor(project_root, contexts_filename)
            p.process()
        else:
            if force:
                self.context_processors[project_root].process()

    def open(self, filename, line=None, contexts=None):
        editor = Editor(self.snaked_conf)
        self.editors.append(editor)
        editor.session = self.session

        connect_all(self, editor)

        idle(self.set_editor_prefs, editor, filename, contexts)
        idle(self.set_editor_shortcuts, editor)
        idle(self.plugin_manager.editor_created, editor)

        self.manage_editor(editor)

        idle(editor.load_file, filename, line)
        idle(self.plugin_manager.editor_opened, editor)

        return editor

    @lazy_property
    def lang_prefs(self):
        return prefs.load_json_settings('langs.conf', {})

    def set_editor_prefs(self, editor, filename, lang_id=None):
        lang = None
        editor.lang = 'default'
        editor.contexts = [editor.lang]

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
                editor.lang = lang.get_id()

        if not lang:
            lang = self.lang_manager.guess_language(filename, None)
            if lang:
                editor.lang = lang.get_id()

        editor.contexts = [editor.lang]

        if lang:
            editor.buffer.set_language(lang)

        if self.session:
            editor.contexts.append('session:' + self.session)

        if root in self.ctx_contexts:
            for ctx, matcher in self.ctx_contexts[root].items():
                if matcher.search(filename):
                    editor.contexts.append(ctx)

        pref = prefs.CompositePreferences(self.lang_prefs.get(editor.lang, {}),
            self.lang_prefs.get('default', {}), prefs.default_prefs.get(editor.lang, {}),
            prefs.default_prefs['default'])

        style_scheme = self.style_manager.get_scheme(pref['style'])
        editor.buffer.set_style_scheme(style_scheme)

        font = pango.FontDescription(pref['font'])
        editor.view.modify_font(font)

        editor.view.set_auto_indent(pref['auto-indent'])
        editor.view.set_indent_on_tab(pref['indent-on-tab'])
        editor.view.set_insert_spaces_instead_of_tabs(not pref['use-tabs'])
        editor.view.set_smart_home_end(pref['smart-home-end'])
        editor.view.set_highlight_current_line(pref['highlight-current-line'])
        editor.view.set_show_line_numbers(pref['show-line-numbers'])
        editor.view.set_tab_width(pref['tab-width'])
        editor.view.set_draw_spaces(pref['show-whitespace'])
        editor.view.set_right_margin_position(pref['right-margin'])
        editor.view.set_show_right_margin(pref['show-right-margin'])
        editor.view.set_wrap_mode(gtk.WRAP_WORD if pref['wrap-text'] else gtk.WRAP_NONE)
        editor.view.set_pixels_above_lines(pref['line-spacing'])

        editor.prefs = pref

    @Editor.editor_closed(idle=True)
    def on_editor_closed(self, editor):
        editor.on_close()
        self.plugin_manager.editor_closed(editor)
        self.editors.remove(editor)

        if not self.editors:
            snaked.core.quick_open.quick_open(self.get_fake_editor())

    @Editor.change_title
    def on_editor_change_title(self, editor, title):
        self.set_editor_title(editor, title)

    @Editor.request_close
    def on_editor_close_request(self, editor):
        self.close_editor(editor)

    @Editor.request_to_open_file
    def on_request_to_open_file(self, editor, filename, line, lang_id):
        self.add_spot(editor)

        for e in self.editors:
            if e.uri == filename:
                self.focus_editor(e)

                if line is not None:
                    e.goto_line(line + 1)

                break
        else:
            e = self.open(filename, line, lang_id)

        return e

    @Editor.request_transient_for
    def on_request_transient_for(self, editor, window):
        self.set_transient_for(editor, window)

    @Editor.settings_changed(idle=True)
    def on_editor_settings_changed(self, editor):
        self.set_editor_prefs(editor, editor.uri, editor.lang)
        for e in self.editors:
            if e is not editor:
                idle(self.set_editor_prefs, e, e.uri, e.lang)

    def new_file_action(self, editor):
        from snaked.core.gui import new_file
        new_file.show_create_file(editor)

    def quit(self, editor):
        for e in self.editors:
            e.on_close()
            self.plugin_manager.editor_closed(e)

        self.save_conf(editor)

        self.plugin_manager.quit()

        for q in self.on_quit:
            try:
                q()
            except:
                import traceback
                traceback.print_exc()

        if gtk.main_level() > 0:
            gtk.main_quit()

    @Editor.push_escape_callback
    def on_push_escape_callback(self, editor, callback, args):
        key = (callback,) + tuple(map(weakref.ref, args))
        if key in self.escape_map:
            return

        self.escape_map[key] = True
        self.escape_stack.append((key, callback, map(weakref.ref, args)))

    def process_escape(self, editor):
        while self.escape_stack:
            key, cb, args = self.escape_stack.pop()
            del self.escape_map[key]
            realargs = [a() for a in args]
            if not any(a is None for a in realargs):
                cb(editor, *realargs)
                return False

        return False

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

    @Editor.plugins_changed
    def on_plugins_changed(self, editor):
        for e in self.editors:
            self.set_editor_shortcuts(e)

    def get_fake_editor(self):
        self.fake_editor = FakeEditor(self)
        return self.fake_editor

    def add_spot_with_feedback(self, editor):
        self.add_spot(editor)
        editor.message('Spot added')

    @Editor.add_spot_request
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
        e = editor.open_file(join_to_settings_dir('snaked.conf'), lang_id='python')
        e.file_saved.connect(self, 'on_config_saved')

    def show_session_preferences(self, editor):
        self.save_conf(editor)
        e = editor.open_file(join_to_settings_dir(self.session + '.session'), lang_id='python')
        e.file_saved.connect(self, 'on_config_saved')

    def on_config_saved(self, editor):
        editor.message('Config updated')
        self.load_conf()

    def edit_contexts(self, editor):
        import shutil
        from os.path import join, exists, dirname
        from snaked.util import make_missing_dirs

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


class FakeEditor(object):
    def __init__(self, manager):
        self.project_root = None
        self.manager = manager
        self.request_transient_for = self
        self.session = manager.session
        self.snaked_conf = manager.snaked_conf

    def emit(self, window):
        self.manager.set_transient_for(self, window)

    def open_file(self, filename, line=None):
        result = self.manager.open(filename, line)
        del self.manager.fake_editor
        self.manager.fake_editor = None
        return result

    def on_dialog_escape(self, dialog):
        self.manager.quit(None)

    def message(self, message, timeout=None):
        print message

    def get_project_root(*args, **kwargs):
        return None
