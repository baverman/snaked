default_prefs = {
    'font': 'Monospace 11',
    'use-tabs': True,
    'tab-width': 4,
    'right-margin': 100,
    'show-line-numbers': True,
    'wrap-text': False,
    'style': 'babymate',
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
