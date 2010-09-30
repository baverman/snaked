import os.path

import gtk
import gtksourceview2
import pango

from ..util import save_file, idle, get_project_root, refresh_gui
from ..signals import SignalManager, Signal, connect_all, connect_external

from .prefs import Preferences, LangPreferences
from .shortcuts import ShortcutManager, ShortcutActivator, ContextShortcutActivator
from .plugins import PluginManager

class Editor(SignalManager):
    editor_closed = Signal()
    request_to_open_file = Signal(str, return_type=object)
    get_title = Signal(return_type=str)
    before_close = Signal()
    file_loaded = Signal()
    change_title = Signal(str) 
    request_transient_for = Signal(object)

    def __init__(self):    
        self.uri = None
        
        self.widget = gtk.ScrolledWindow()
        self.widget.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
                
        self.buffer = gtksourceview2.Buffer()

        self.view = gtksourceview2.View()
        self.view.set_buffer(self.buffer)
        self.widget.add(self.view)

        self.widget.show_all()
        
        connect_all(self, buffer=self.buffer)

    def update_title(self):
        modified = '*' if self.buffer.get_modified() else ''
        
        if self.uri:
            title = self.get_title.emit()

            if not title:
                title = self.uri
        else:
            title = 'Unknown'
        
        self.change_title.emit(modified + title)          

    def load_file(self, filename):
        self.uri = os.path.abspath(filename)
        
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
            save_file(self.uri, self.buffer.get_text(*self.buffer.get_bounds()), 'utf-8')
            self.buffer.set_modified(False)

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
        if not self.buffer.get_modified() and self.text == u'':
            self.close()
            
        return editor

    @property
    def cursor(self):
        return self.buffer.get_iter_at_mark(self.buffer.get_insert())

    @property
    def text(self):
        return self.buffer.get_text(*self.buffer.get_bounds())
        
        
class EditorManager(object):
    def __init__(self):
        self.editors = []
        self.style_manager = gtksourceview2.style_scheme_manager_get_default()
        self.lang_manager = gtksourceview2.language_manager_get_default()
        
        self.shortcuts = self.get_shortcut_manager()
        self.plugin_manager = PluginManager()
        
        self.prefs = Preferences()
        self.lang_prefs = {}

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

        return shortcuts
        
    def open(self, filename):
        editor = self.create_editor()
        self.editors.append(editor)
        
        connect_all(self, editor)

        idle(self.set_editor_prefs, editor, filename)
        idle(self.set_editor_shortcuts, editor)
        idle(self.plugin_manager.editor_opened, editor)
        
        self.manage_editor(editor)
        
        if filename:
            idle(editor.load_file, filename)
        
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
        
    def quit(self, *args):
        [self.close_editor(e) for e in self.editors]


class TabbedEditorManager(EditorManager):
    def __init__(self):
        super(TabbedEditorManager, self).__init__()

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect('delete-event', self.on_delete_event)

        self.window.set_property('default-width', 800)
        self.window.set_property('default-height', 500)
    
        self.activator = ContextShortcutActivator(self.window, self.get_context, self.shortcut_validator)
        
        self.note = gtk.Notebook()
        self.note.set_property('tab-hborder', 5)
        
        self.window.add(self.note)
        
        self.window.show_all()
    
    def get_context(self):
        widget = self.note.get_nth_page(self.note.get_current_page())
        for e in self.editors:
            if e.widget is widget:
                return (e,)

        raise Exception('Editor not found')
    
    def shortcut_validator(self, ctx, key, modifier):
        plugin = self.plugin_manager.get_plugin_by_key(key, modifier)
        return not plugin or self.plugin_manager.plugin_is_for_editor(plugin, ctx[0])

    def manage_editor(self, editor):
        self.note.append_page(editor.widget)
        self.focus_editor(editor)
        editor.view.grab_focus()
       
    def create_editor(self):
        return Editor()

    def focus_editor(self, editor):
        idx = self.note.page_num(editor.widget)
        self.note.set_current_page(idx)

    def update_top_level_title(self):
        idx = self.note.get_current_page()
        self.window.set_title(self.note.get_tab_label_text(self.note.get_nth_page(idx)))        
                
    def set_editor_title(self, editor, title):
        self.note.set_tab_label_text(editor.widget, title)
        if self.note.get_current_page() == self.note.page_num(editor.widget):
            self.update_top_level_title()

    def on_delete_event(self, *args):
        self.quit()

    def close_editor(self, editor):
        idx = self.note.page_num(editor.widget)
        self.note.remove_page(idx)
        editor.editor_closed.emit()

    def set_editor_shortcuts(self, editor):
        self.plugin_manager.bind_shortcuts(self.activator, editor)

        if hasattr(self, 'editor_shortcuts_binded'):
            return
        
        self.editor_shortcuts_binded = True

        self.shortcuts.bind(self.activator, 'quit', self.quit)
        self.shortcuts.bind(self.activator, 'close-window', self.close_editor)
        self.shortcuts.bind(self.activator, 'save', self.save)

    def save(self, editor):
        editor.save()

    def set_transient_for(self, editor, window):
        window.set_transient_for(self.window)
