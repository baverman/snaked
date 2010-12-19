import anydbm
import os.path
import os
import json

from snaked.util import make_missing_dirs, join_to_settings_dir

default_prefs = {
    'default': {
        'font': 'Monospace 11',
        'use-tabs': True,
        'tab-width': 4,
        'show-right-margin': False,
        'right-margin': 100,
        'show-line-numbers': True,
        'wrap-text': False,
        'style': 'classic',
        'auto-indent': True,
        'indent-on-tab': True,
        'smart-home-end': True,
        'highlight-current-line': True,
        'show-whitespace': False,
        'line-spacing': 0,
        'remove-trailing-space': False,
    },
    'python': {
        'use-tabs': False,
        'show-right-margin': True,
        'remove-trailing-space': True,
    },
    'snippets': {
        'use-tabs': True,
        'remove-trailing-space': False,
    },
    'rst': {
        'use-tabs': False,
        'tab-width': 3,
        'remove-trailing-space': False,
        'right-margin': 80,
        'show-right-margin': True,
    }
}

registered_dialogs = {}

def register_dialog(name, callback, *keywords):
    registered_dialogs[name] = keywords, callback

def load_json_settings(name, default=None):
    filename = get_settings_path(name)
    try:
        with open(filename) as f:
            try:
                return json.load(f)
            except ValueError:
                pass
    except IOError:
        pass

    return default

def save_json_settings(name, value):
    filename = get_settings_path(name)
    with open(filename, 'w') as f:
        json.dump(value, f, sort_keys=True, indent=4)

def get_settings_path(name):
    filename = join_to_settings_dir(name)
    make_missing_dirs(filename)
    return filename


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


class KVSettings(object):
    def __init__(self, name):
        self.db = anydbm.open(get_settings_path(name), 'c')

    def get_key(self, key):
        if isinstance(key, unicode):
            return key.encode('utf-8')
        else:
            return key

    def __getitem__(self, key):
        return self.db[self.get_key(key)]

    def __contains__(self, key):
        return self.db.has_key(self.get_key(key))

    def __setitem__(self, key, value):
        self.db[self.get_key(key)] = value

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


class PySettings(object):
    def __init__(self):
        self.data = {}
        self.sources = []

    def clear(self):
        self.data.clear()
        self.sources[:] = []

    def __getitem__(self, name):
        for s in self.sources:
            try:
                return self.data[s][name]
            except KeyError:
                pass

        value = getattr(self.__class__, name, None)
        if value is None:
            raise KeyError()

        return value

    def __setitem__(self, name, value):
        self.data[self.sources[0]][name] = value

    def __contains__(self, name):
        return any(name in self.data[s] for s in self.sources) or \
            ( getattr(self.__class__, name, None) is not None and not self.is_special(name) )

    def is_special(self, name):
        return name.startswith('_') or name.lower().endswith('_doc')

    def is_default(self, source, name):
        return name not in self.data[source] and \
            getattr(self.__class__, name, None) is not None and not self.is_special(name)

    def get_config(self, source, parent_source=None):
        result = ''
        for name in sorted(self.__class__.__dict__):
            if name not in self:
                continue

            doc = getattr(self.__class__, name + '_doc', None)
            if not doc:
                doc = getattr(self.__class__, name + '_DOC', None)
            if doc:
                result += '# ' + doc + '\n'

            write_value = True
            is_default = False

            if name in self.data[source]:
                value = self.data[source][name]
            elif parent_source and name in self.data[parent_source]:
                value = self.data[parent_source][name]
                is_default = True
            else:
                value = getattr(self.__class__, name, None)
                is_default = True
                if value is None:
                    write_value = False

            if write_value:
                value = '%s = %s' % (name, repr(value))
                if is_default:
                    value = '# ' + value

                result += value + '\n\n'

        return result

    def add_source(self, source, data):
        self.sources.insert(0, source)
        self.data[source] = data

    def load(self, name):
        filename = get_settings_path(name)
        data = {}
        try:
            execfile(filename, data)
        except IOError:
            pass
        except SyntaxError, e:
            print 'Error on loading config: %s' % filename, e

        self.add_source(name, data)

    def save(self):
        ps = None
        for s in reversed(self.sources):
            filename = get_settings_path(s)
            with open(filename, 'w') as f:
                f.write(self.get_config(s, ps))

            ps = s
