import anydbm
import os.path
import json
from itertools import chain
from inspect import cleandoc

from uxie.utils import make_missing_dirs, join_to_settings_dir

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

def get_settings_path(*name):
    filename = join_to_settings_dir('snaked', *name)
    make_missing_dirs(filename)
    return filename


options = {}
def add_option(name, default, desc=''):
    options[name] = (default, desc)

internal_options = {}
def add_internal_option(name, default, desc=''):
    internal_options[name] = (default, desc)

def add_editor_preferences(on_dialog_created, on_pref_refresh, default_values):
    import snaked.core.gui.editor_prefs

    for k, v in default_values.iteritems():
        default_prefs.setdefault(k, {}).update(v)

    snaked.core.gui.editor_prefs.on_dialog_created_hooks.append(on_dialog_created)
    snaked.core.gui.editor_prefs.on_pref_refresh_hooks.append(on_pref_refresh)

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

    def __setitem__(self, key, value):
        for p in self.prefs:
            if key in p:
                p[key] = value
                return

        raise KeyError('There is no %s in preferences' % key)

    def __contains__(self, key):
        raise NotImplementedError()


class KVSettings(object):
    def __init__(self, *name):
        self.db = anydbm.open(get_settings_path(*name), 'cu')

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

    def save(self):
        self.db.sync()

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


class DefaultValue(object):
    def __init__(self, name, default, additional=None):
        self.default = default

        if additional is None:
            self.additional = self.get_default()
        else:
            self.additional = additional

        self.name = name

    def __repr__(self):
        return 'default[%s] + %s' % (self.name, repr(self.additional))


class DefaultListValue(DefaultValue):
    def get_default(self):
        return []

    def __add__(self, x):
        return DefaultListValue(self.name, self.default + x, x, True)

    def __iter__(self, x):
        return iter(self.default)


class DefaultDictValue(DefaultValue):
    def get_default(self):
        return {}

    def __add__(self, x):
        comp = self.default.copy()
        return DefaultListValue(self.name, comp.update(x), x, True)

    def __getitem__(self, name):
        return self.default[name]

    def __contains__(self, name):
        return name in self.default

    def __setitem__(self, name, value):
        self.additional[name] = value
        self.default[name] = value


class DefaultValuesProvider(object):
    def __init__(self, conf):
        self.conf = conf

    def __getitem__(self, name):
        v = self.conf[name]
        if isinstance(v, list):
            return DefaultListValue(name, v)
        if isinstance(v, dict):
            return DefaultDictValue(name, v)
        else:
            return v


class PySettings(object):
    def __init__(self, options=None, parent=None):
        assert options or parent
        if parent:
            self.parent = parent
            self.options = parent.options
        else:
            self.options = options
            self.parent = None

        self.data = {}

    def __getitem__(self, name):
        try:
            return self.data[name]
        except KeyError:
            pass

        if self.parent:
            v = self.parent[name]
            if isinstance(v, list):
                v = v[:]
            elif isinstance(v, dict):
                v = v.copy()
        else:
            v = self.get_default(name)

        self.data[name] = v
        return v

    def __contains__(self, name):
        return name in self.options

    def get_default(self, name):
        value = self.options[name][0]
        if callable(value):
            value = value()

        return value

    def __setitem__(self, name, value):
        self.data[name] = value

    def get_config(self):
        result = ''
        for name in sorted(set(chain(self.data, self.options))):
            doc = cleandoc(self.options.get(name, (0, 'Unknown option'))[1])
            if doc:
                for l in doc.splitlines():
                    result += '# ' + l + '\n'

            if name not in self.options:
                value = self.data[name]
                is_default = False
            elif name not in self.data:
                is_default = True
                if self.parent:
                    value = self.parent[name]
                else:
                    value = self.get_default(name)
            else:
                value = self.data[name]
                if (self.parent and value == self.parent[name]) or (
                        not self.parent and value == self.get_default(name)):
                    is_default = True
                else:
                    is_default = False

            value = '%s = %s' % (name, repr(value))
            if is_default:
                value = '# ' + value

            result += value + '\n\n'

        return result

    def load(self, filename):
        self.filename = filename
        self.data.clear()

        if self.parent:
            self.data['default'] = DefaultValuesProvider(self.parent)

        try:
            execfile(self.filename, self.data)
        except IOError:
            pass
        except SyntaxError, e:
            print 'Error on loading config: %s' % self.filename, e

        try:
            del self.data['__builtins__']
        except KeyError:
            pass

        if self.parent:
            del self.data['default']

    def save(self):
        with open(self.filename, 'w') as f:
            f.write(self.get_config())
