import os.path
import weakref

import gtk
import gtksourceview2
import pango

from ..util import save_file, idle, get_project_root, lazy_property
from ..signals import SignalManager, Signal, connect_all, connect_external

from .prefs import Preferences, LangPreferences
from .shortcuts import ShortcutManager
from .plugins import PluginManager

class Editor(SignalManager):
    editor_closed = Signal()
    request_to_open_file = Signal(str, return_type=object)
    request_close = Signal()
    get_title = Signal(return_type=str)
    before_close = Signal()
    file_loaded = Signal()
    change_title = Signal(str) 
    request_transient_for = Signal(object)
    file_saved = Signal()
    push_escape_callback = Signal(object, object)

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
            
            self.buffer.place_cursor(self.buffer.get_start_iter())
            self.view.window.thaw_updates()

        self.file_loaded.emit()
                
        self.update_title()
        
    @connect_external('buffer', 'modified-changed', idle=True)
    def on_modified_changed(self, *args):
        self.update_title()
            
    def save(self):
        if self.uri:
            try:
                save_file(self.uri, self.buffer.get_text(*self.buffer.get_bounds()), 'utf-8')
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
        self.feedback_popup.show(message, timeout)

    def push_escape(self, callback, *args):
        self.push_escape_callback.emit(callback, args)
        
class EditorManager(object):
    def __init__(self):
        self.editors = []
        self.style_manager = gtksourceview2.style_scheme_manager_get_default()
        self.lang_manager = gtksourceview2.language_manager_get_default()
        
        self.shortcuts = self.get_shortcut_manager()
        self.plugin_manager = PluginManager()
        
        self.prefs = Preferences()
        self.lang_prefs = {}
        
        self.escape_stack = []
        self.escape_map = {}
        
        self.session = None

    def get_lang_prefs(self, lang_id):
        try:
            return self.lang_prefs[lang_id]
        except KeyError:
            self.lang_prefs[lang_id] = LangPreferences(lang_id, self.prefs)
            return self.lang_prefs[lang_id]
    
    def get_shortcut_manager(self):
        shortcuts = ShortcutManager()
        shortcuts.add('quit', '<ctrl>q', 'Application', 'Quit')        
        shortcuts.add('close-window', '<ctrl>w', 'Window', 'Closes window')
        shortcuts.add('save', '<ctrl>s', 'File', 'Saves file')
        shortcuts.add('next-editor', '<alt>Right', 'Window', 'Switches to next editor')
        shortcuts.add('prev-editor', '<alt>Left', 'Window', 'Switches to previous editor')
        shortcuts.add('new-file', '<ctrl>n', 'File', 'Open dialog to choose new file directory and name')

        return shortcuts
        
    def open(self, filename):
        editor = self.create_editor()
        self.editors.append(editor)
        
        connect_all(self, editor)

        idle(self.set_editor_prefs, editor, filename)
        idle(self.set_editor_shortcuts, editor)
        
        self.manage_editor(editor)
        
        if filename:
            idle(editor.load_file, filename)

        idle(self.plugin_manager.editor_opened, editor)
        
        return editor
    
    def set_editor_prefs(self, editor, filename):
        if filename:
            lang = self.lang_manager.guess_language(filename, None)
            editor.buffer.set_language(lang)
        else:
            lang = None
        
        if lang:
            editor.lang = lang.get_id()
            prefs = self.get_lang_prefs(lang.get_id())
        else:
            editor.lang = None
            prefs = self.prefs
        
        style_scheme = self.style_manager.get_scheme(prefs['style'])
        editor.buffer.set_style_scheme(style_scheme)
        
        font = pango.FontDescription(prefs['font'])
        editor.view.modify_font(font)
        
        editor.view.set_auto_indent(prefs['auto-indent'])
        editor.view.set_indent_on_tab(prefs['indent-on-tab'])
        editor.view.set_insert_spaces_instead_of_tabs(not prefs['use-tabs'])
        editor.view.set_smart_home_end(prefs['smart-home-end'])
        editor.view.set_highlight_current_line(prefs['highlight-current-line'])
        editor.view.set_show_line_numbers(prefs['show-line-numbers'])
        editor.view.set_tab_width(prefs['tab-width'])
        editor.view.set_draw_spaces(prefs['show-whitespace'])
        
        right_margin = prefs['right-margin']
        if right_margin:
            editor.view.set_right_margin_position(right_margin)
            editor.view.set_show_right_margin(True)
        else:
            editor.view.set_show_right_margin(False)

    @Editor.editor_closed(idle=True)
    def on_editor_closed(self, editor):
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
        
    def new_file_action(self, editor):
        dialog = gtk.FileChooserDialog('Create file', None, gtk.FILE_CHOOSER_ACTION_SAVE,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK))
        
        root = editor.project_root
        if root:
            dialog.set_current_folder(root)

        dialog.set_do_overwrite_confirmation(True)
        self.set_transient_for(editor, dialog)
        
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.open(dialog.get_filename())
            
        dialog.destroy()
        
    def quit(self, *args):
        if self.session:
            self.save_session(self.session)
            
        [self.close_editor(e) for e in self.editors]

    def open_session(self, session):
        self.session = session
        from .prefs import ListSettings
        settings = ListSettings('session-%s.db' % session)
        files = settings.load()

        if files:        
            for f in files:
                self.open(f)
        else:
            self.open(None)
                    
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