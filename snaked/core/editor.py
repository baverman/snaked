import os.path
import weakref

import gtk
import gtksourceview2
import pango

from ..util import save_file, idle, get_project_root, lazy_property
from ..signals import SignalManager, Signal, connect_all, connect_external

import prefs
from .shortcuts import register_shortcut, load_shortcuts
from .plugins import PluginManager

class Editor(SignalManager):
    editor_closed = Signal()
    request_to_open_file = Signal(str, return_type=object)
    request_close = Signal()
    settings_changed = Signal()
    get_title = Signal(return_type=str)
    get_file_position = Signal(return_type=int)
    before_close = Signal()
    file_loaded = Signal()
    change_title = Signal(str) 
    request_transient_for = Signal(object)
    file_saved = Signal()
    push_escape_callback = Signal(object, object)
    plugins_changed = Signal()

    def __init__(self):    
        self.uri = None
        
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
                
        self.buffer = gtksourceview2.Buffer()

        self.view = gtksourceview2.View()
        self.view.set_buffer(self.buffer)
        sw.add(self.view)


        self.widget = gtk.VBox(False, 0)
        self.widget.pack_start(sw)

        self.widget.show_all()
        
        connect_all(self, buffer=self.buffer)

    def update_title(self):
        modified = '*' if self.buffer.get_modified() else ''
        
        if self.uri:
            title = self.get_title.emit()

            if not title:
                title = os.path.basename(self.uri)
        else:
            title = 'Unknown'
        
        self.change_title.emit(modified + title)          

    def load_file(self, filename):
        self.uri = os.path.abspath(filename)
        
        if os.path.exists(self.uri):
            self.view.window.freeze_updates()        
            self.on_modified_changed_handler.block()
            self.buffer.begin_not_undoable_action()
            
            self.buffer.set_text(open(filename).read().decode('utf-8'))
            self.buffer.set_modified(False)
            
            self.buffer.end_not_undoable_action()
            self.on_modified_changed_handler.unblock()
            self.view.window.thaw_updates()
            
            pos = self.get_file_position.emit()
            if pos is not None and pos >= 0:
                self.buffer.place_cursor(self.buffer.get_iter_at_line(pos))
                self.view.scroll_to_mark(self.buffer.get_insert(), 0.001, use_align=True, xalign=1.0)
            else:
                self.buffer.place_cursor(self.buffer.get_start_iter())
                
        self.file_loaded.emit()
                
        self.update_title()
        
    @connect_external('buffer', 'modified-changed', idle=True)
    def on_modified_changed(self, *args):
        self.update_title()
            
    def save(self):
        if self.uri:
            try:
                save_file(self.uri, self.buffer.get_text(*self.buffer.get_bounds()), 'utf-8')
                if not self.buffer.get_modified():
                    self.message("%s saved" % self.uri)
                self.buffer.set_modified(False)
                self.file_saved.emit()
            except Exception, e:
                self.message(str(e), 5000)

    @property
    def project_root(self):
        if self.uri:
            root = get_project_root(self.uri)
            if not root:
                root = os.path.dirname(self.uri)
          
            return root 
            
        return None

    def open_file(self, filename):        
        editor = self.request_to_open_file.emit(filename)
        if not self.uri and not self.buffer.get_modified() and self.text == u'':
            self.request_close.emit()
            
        return editor

    @property
    def cursor(self):
        return self.buffer.get_iter_at_mark(self.buffer.get_insert())

    @property
    def text(self):
        return self.buffer.get_text(*self.buffer.get_bounds())

    def goto_line(self, line):
        iterator = self.buffer.get_iter_at_line(line - 1)
        self.buffer.place_cursor(iterator)
        self.view.scroll_to_iter(iterator, 0.001, use_align=True, xalign=1.0)

    @lazy_property
    def feedback_popup(self):
        from .feedback import FeedbackPopup
        return FeedbackPopup(self.view)
                
    def message(self, message, timeout=1500):
        popup = self.feedback_popup
        popup.show(message, timeout)
        self.push_escape(popup.hide)

    def push_escape(self, callback, *args):
        self.push_escape_callback.emit(callback, args)
        
class EditorManager(object):
    def __init__(self):
        self.editors = []
        self.style_manager = gtksourceview2.style_scheme_manager_get_default()
        self.lang_manager = gtksourceview2.language_manager_get_default()
        
        self.plugin_manager = PluginManager()
        prefs.register_dialog('Plugins', self.plugin_manager.show_plugins_prefs, 'plugin',
            'extension')
            
        prefs.register_dialog('Key configuration', self.show_key_preferences, 'key', 'bind', 'shortcut')

        prefs.register_dialog('Editor settings', self.show_editor_preferences,
            'editor', 'font', 'style', 'margin', 'line', 'tab', 'whitespace')
        
        self.escape_stack = []
        self.escape_map = {}
        
        self.session = None

        load_shortcuts()
        self.register_app_shortcuts()

    def register_app_shortcuts(self):
        register_shortcut('quit', '<ctrl>q', 'Application', 'Quit')        
        register_shortcut('close-window', '<ctrl>w', 'Window', 'Closes window')
        register_shortcut('save', '<ctrl>s', 'File', 'Saves file')
        register_shortcut('next-editor', '<alt>Right', 'Window', 'Switches to next editor')
        register_shortcut('prev-editor', '<alt>Left', 'Window', 'Switches to previous editor')
        register_shortcut('new-file', '<ctrl>n', 'File',
            'Open dialog to choose new file directory and name')
        register_shortcut('show-preferences', '<ctrl>p', 'Window', 'Open preferences dialog')
        
    def open(self, filename):
        editor = Editor()
        self.editors.append(editor)
        
        connect_all(self, editor)

        idle(self.set_editor_prefs, editor, filename)
        idle(self.set_editor_shortcuts, editor)
        idle(self.plugin_manager.editor_created, editor)
        
        self.manage_editor(editor)
        
        if filename:
            idle(editor.load_file, filename)

        idle(self.plugin_manager.editor_opened, editor)
        
        return editor

    @lazy_property
    def lang_prefs(self):
        return prefs.load_json_settings('langs.conf', {})
    
    def set_editor_prefs(self, editor, filename):
        if filename:
            lang = self.lang_manager.guess_language(filename, None)
            editor.buffer.set_language(lang)
        else:
            lang = None
            
        editor.lang = lang.get_id() if lang else 'default'
        
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

    @Editor.editor_closed(idle=True)
    def on_editor_closed(self, editor):
        if self.session and len(self.editors) == 1:
            self.save_session(self.session)
            self.session = None
        
        self.plugin_manager.editor_closed(editor)
        self.editors.remove(editor)
        
        if not self.editors:
            self.plugin_manager.quit()
            gtk.main_quit()

    @Editor.change_title
    def on_editor_change_title(self, editor, title):
        self.set_editor_title(editor, title)

    @Editor.request_close
    def on_editor_close_request(self, editor):
        self.close_editor(editor)
    
    @Editor.request_to_open_file
    def on_request_to_open_file(self, editor, filename):
        for e in self.editors:
            if e.uri == filename:
                self.focus_editor(e)
                break
        else:
            e = self.open(filename)
        
        return e

    @Editor.request_transient_for
    def on_request_transient_for(self, editor, window):
        self.set_transient_for(editor, window)

    @Editor.settings_changed(idle=True)
    def on_editor_settings_changed(self, editor):
        self.set_editor_prefs(editor, editor.uri)
        for e in self.editors:
            if e is not editor:
                idle(self.set_editor_prefs, e, e.uri)
        
    def new_file_action(self, editor):
        from snaked.core.gui import new_file
        new_file.show_create_file(editor)
        
    def quit(self, *args):
        if self.session:
            self.save_session(self.session)
            self.session = None
            
        [self.close_editor(e) for e in self.editors]

    def get_session_files(self, session):
        self.session = session
        from .prefs import ListSettings
        settings = ListSettings('session-%s.db' % session)
        return settings.load()
                    
    def save_session(self, session):
        from .prefs import ListSettings
        settings = ListSettings('session-%s.db' % session)
        settings.store(e.uri for e in self.editors if e.uri)

    @Editor.push_escape_callback
    def on_push_escape_callback(self, editor, callback, args):
        key = (callback,) + tuple(map(id, args))
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
                cb(*realargs)
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