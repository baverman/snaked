import anydbm
import os.path
import os

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


class Preferences(object):
    def __init__(self):
        pass
        
    def __getitem__(self, key):
        return default_prefs[key]

    
class LangPreferences(object):
    def __init__(self, lang_id, prefs):
        self.prefs = prefs
        self.lang_prefs = lang_default_prefs.get(lang_id, {})
    
    def __getitem__(self, key):
        try:
            return self.lang_prefs[key]
        except KeyError:
            return self.prefs[key]

class KVSettings(object):
    def __init__(self, name):
        path = os.path.join(os.path.expanduser("~"), '.local', 'snaked')
        if not os.path.exists(path):
            os.makedirs(path, mode=0755)
            
        dbname = os.path.join(path, name)
        self.db = anydbm.open(dbname, 'c')
    
    def __getitem__(self, key):
        return self.db[key]
    
    def __contains__(self, key):
        return key in self.db
    
    def __setitem__(self, key, value):
        self.db[key] = value
    
    def __del__(self):
        self.db.close()
