import anydbm
import os.path
import os

import weakref

from snaked.util import BuilderAware, join_to_file_dir, idle, refresh_gui

default_prefs = {
    'font': 'Monospace 11',
    'use-tabs': True,
    'tab-width': 4,
    'right-margin': 100,
    'show-line-numbers': True,
    'wrap-text': False,
    'style': 'babymate',
    'auto-indent': True,
    'indent-on-tab': True,
    'smart-home-end': True,
    'highlight-current-line': True,
    'show-whitespace': False,
}

lang_default_prefs = {
    'python': {
        'use-tabs': False,
    }
}

registered_dialogs = {}

def register_dialog(name, callback, *keywords):
    registered_dialogs[name] = keywords, callback


class CompositePreferences(object):
    def __init__(self, *prefs):
        self.prefs = prefs
    
    def __getitem__(self, key):
        for p in self.prefs:
            try:
                return p[key]
            except KeyError:
                pass
                
        raise KeyError('There is no %s in preferences' % key)

def get_settings_path(name):
    path = os.path.join(os.path.expanduser("~"), '.local', 'snaked')
    if not os.path.exists(path):
        os.makedirs(path, mode=0755)
        
    return os.path.join(path, name)
    

class KVSettings(object):
    def __init__(self, name):
        self.db = anydbm.open(get_settings_path(name), 'c')
    
    def __getitem__(self, key):
        return self.db[key]
    
    def __contains__(self, key):
        return self.db.has_key(key)
    
    def __setitem__(self, key, value):
        self.db[key] = value
    
    def __del__(self):
        self.db.close()

class ListSettings(object):
    def __init__(self, name):
        self.path = get_settings_path(name)

    def exists(self):
        return os.path.exists(self.path)
    
    def load(self):
        try:
            return [l.strip() for l in open(self.path)]
        except IOError:
            return []
    
    def store(self, data):
        open(self.path, 'w').write('\n'.join(data))


class PreferencesDialog(BuilderAware):
    def __init__(self):
        BuilderAware.__init__(self, join_to_file_dir(__file__, 'prefs.glade'))
        
        from snaked.core.shortcuts import ShortcutActivator
        self.activator = ShortcutActivator(self.window)
        self.activator.bind('Escape', self.hide)
        self.activator.bind('Return', self.activate)
        
    def hide(self):
        self.window.destroy()
        
    def show(self, editor):
        self.editor = weakref.ref(editor)
        editor.request_transient_for.emit(self.window)
        self.fill_dialogs(None)
        self.window.present()
        
    def fill_dialogs(self, search):
        self.dialogs.clear()
        
        for name, (keywords, show_func) in registered_dialogs.iteritems():
            if not search or any(w.startswith(search) for w in keywords):
                self.dialogs.append((name, ))
        
    def on_delete_event(self, *args):
        return False
        
    def on_search_entry_changed(self, *args):
        search = self.search_entry.get_text().strip().lower()
        idle(self.fill_dialogs, search)
        
    def activate(self):
        (model, iter) = self.dialogs_view.get_selection().get_selected()
        name = model.get_value(iter, 0)
        registered_dialogs[name][1](self.editor())
        refresh_gui()
        idle(self.hide)