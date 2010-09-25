import gtk
import gtksourceview2
import pango

from gsignals import connect_all

from ..util import save_file

from .signals import EditorSignals
from .prefs import Preferences, LangPreferences
from .shortcuts import ShortcutManager, ShortcutActivator


class Editor(object):
    """
    The main editor window.
    
    Editor can be both standalone window and embedded into tab. 
    """
    
    def __init__(self):    
        self.signals = EditorSignals()
        
        self.uri = None
        
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect('delete-event', self.on_delete_event)
        self.window.connect('destroy', self.on_destroy)

        self.activator = ShortcutActivator(self.window)
        
        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        self.window.add(scrolled_window)
                
        self.buffer = gtksourceview2.Buffer()
        
        self.view = gtksourceview2.View()
        self.view.set_buffer(self.buffer)
        scrolled_window.add(self.view)

        self.window.show_all()

    def init_shortcuts(self, manager):
        manager.bind(self.activator, 'close-window', self.close)
        manager.bind(self.activator, 'save', self.save)

    def load_file(self, filename):
        self.uri = filename
        
        self.buffer.begin_not_undoable_action()
        self.buffer.set_text(open(filename).read().decode('utf-8'))
        self.buffer.end_not_undoable_action()
        
        self.buffer.place_cursor(self.buffer.get_start_iter())
        
        self.window.set_title(filename)
        
    def on_destroy(self, *args):
        self.signals.editor_closed.emit(self)
    
    def on_delete_event(self, *args):
        return False
    
    def close(self):
        self.window.destroy()
        
    def save(self):
        if self.uri:
            save_file(self.uri, self.buffer.get_text(*self.buffer.get_bounds()), 'utf-8')

    @staticmethod
    def register_shortcuts(manager):
        manager.add('close-window', '<ctrl>w', 'Window', 'Closes window')
        manager.add('save', '<ctrl>s', 'File', 'Saves file')
        
        
class EditorManager(object):
    """
    Keeps window editor list
    """
    
    def __init__(self):
        self.editors = []
        self.style_manager = gtksourceview2.style_scheme_manager_get_default()
        self.lang_manager = gtksourceview2.language_manager_get_default()
        
        self.init_shortcut_manager()
        
        self.prefs = Preferences()
        self.lang_prefs = {}

    def get_lang_prefs(self, lang_id):
        try:
            return self.lang_prefs[lang_id]
        except KeyError:
            self.lang_prefs[lang_id] = LangPreferences(lang_id, self.prefs)
            return self.lang_prefs[lang_id]
    
    def init_shortcut_manager(self):
        self.shortcuts = ShortcutManager()
        self.shortcuts.add('quit', '<ctrl>q', 'Application', 'Quit')        
        Editor.register_shortcuts(self.shortcuts)
        
    def open(self, filename):
        editor = Editor()
        self.editors.append(editor)
        connect_all(self, editor.signals)
        
        self.set_editor_prefs(editor, filename)
        self.set_editor_shortcuts(editor)
        
        if filename:
            editor.load_file(filename)
        
        return editor
    
    def set_editor_prefs(self, editor, filename):
        lang = self.lang_manager.guess_language(filename, None)
        editor.buffer.set_language(lang)
        
        prefs = self.get_lang_prefs(lang.get_id())
        
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

    def set_editor_shortcuts(self, editor):
        editor.init_shortcuts(self.shortcuts)
        self.shortcuts.bind(editor.activator, 'quit', self.quit)
    
    @EditorSignals.editor_closed(idle=True)
    def on_editor_closed(self, sender, editor):
        self.editors.remove(editor)
        if not self.editors:
            gtk.main_quit()

    def quit(self):
        [e.close() for e in self.editors]
