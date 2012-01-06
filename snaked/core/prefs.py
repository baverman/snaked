import anydbm, whichdb
import os.path
import json
from itertools import chain
from inspect import cleandoc

import gtk, pango

from uxie.utils import make_missing_dirs, join_to_settings_dir

def init(injector):
    injector.bind('window', 'editor-prefs', 'Prefs/_Editor settings#1', show_editor_preferences)
    injector.bind('window', 'default-config', 'Prefs/Global/_Config', show_default_config)
    injector.bind('window', 'default-contexts', 'Prefs/Global/Conte_xts',
        show_contexts_config, 'default')

    injector.bind('window', 'session-config', 'Prefs/Session/_Config', show_session_config)
    injector.bind('window', 'session-contexts', 'Prefs/Session/Conte_xts',
        show_contexts_config, 'session')

    injector.bind('window', 'project-contexts', 'Prefs/_Project/Conte_xts',
        show_contexts_config, 'project')

    injector.bind_menu('Prefs').to('<ctrl>p')

def show_editor_preferences(window):
    from snaked.core.gui.editor_prefs import PreferencesDialog
    dialog = PreferencesDialog(window.manager.lang_prefs)
    dialog.show(window)

def show_default_config(window):
    window.manager.default_config.save()
    uri = join_to_settings_dir('snaked', 'snaked.conf')
    e = window.manager.open(uri, contexts='python')
    window.attach_editor(e)
    e.connect('file-saved', on_config_saved, window.manager.default_config, uri)

def show_session_config(window):
    window.manager.session_config.save()
    uri = join_to_settings_dir('snaked', window.manager.session, 'config')
    e = window.manager.open(uri, contexts='python')
    window.attach_editor(e)
    e.connect('file-saved', on_config_saved, window.manager.session_config, uri)

def on_config_saved(editor, config, config_path):
    editor.message('Config updated', 'done')
    config.load(config_path)

def show_contexts_config(window, config_type):
    import shutil
    from os.path import join, exists, dirname
    from uxie.utils import make_missing_dirs

    manager = window.manager

    if config_type == 'default':
        processor = manager.default_ctx_processor
    elif config_type == 'session':
        processor = manager.session_ctx_processor
    elif config_type == 'project':
        editor = window.get_editor_context()
        if not editor:
            window.message('Hmm. Project?', 'warn')
            return

        root = editor.project_root
        if not root:
            editor.message('Current project root is not defined', 'warn')
            return

        processor = manager.get_context_manager(root).project_processor
    else:
        raise Exception('Unknown context config type: ' + str(config_type))

    uri = processor.filename
    if not exists(uri):
        make_missing_dirs(uri)
        shutil.copy(join(dirname(__file__), 'contexts.template'), uri)

    e = window.manager.open(uri)
    window.attach_editor(e)
    e.connect('file-saved', on_context_saved)

def on_context_saved(editor):
    editor.message('Contexts updated', 'done')
    for m in editor.window.manager.ctx_managers.values():
        m.invalidate()

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

def update_view_preferences(view, buf):
    # Try to fix screen flickering
    # No hope, should mail bug to upstream
    #text_style = style_scheme.get_style('text')
    #if text_style and editor.view.window:
    #    color = editor.view.get_colormap().alloc_color(text_style.props.background)
    #    editor.view.modify_bg(gtk.STATE_NORMAL, color)

    pref = buf.config

    font = pango.FontDescription(pref['font'])
    view.modify_font(font)

    view.set_auto_indent(pref['auto-indent'])
    view.set_indent_on_tab(pref['indent-on-tab'])
    view.set_insert_spaces_instead_of_tabs(not pref['use-tabs'])
    view.set_smart_home_end(pref['smart-home-end'])
    view.set_highlight_current_line(pref['highlight-current-line'])
    view.set_show_line_numbers(pref['show-line-numbers'])
    view.set_tab_width(pref['tab-width'])
    view.set_draw_spaces(pref['show-whitespace'])
    view.set_right_margin_position(pref['right-margin'])
    view.set_show_right_margin(pref['show-right-margin'])
    view.set_wrap_mode(gtk.WRAP_WORD if pref['wrap-text'] else gtk.WRAP_NONE)
    view.set_pixels_above_lines(pref['line-spacing'])

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
        self.prefs = list(prefs)

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
        filename = get_settings_path(*name)

        # Dirty. Try to avoid locking of gdbm files
        result = whichdb.whichdb(filename)
        if result is None:
            result = anydbm._defaultmod.__name__
        elif result == "":
            raise Exception("db type of %s could not be determined" % filename)

        if result == 'gdbm':
            flags = 'cu'
        else:
            flags = 'c'

        self.db = anydbm.open(filename, flags)

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

    def load(self, default):
        try:
            return [l.strip() for l in open(self.path)]
        except IOError:
            return default

    def store(self, data):
        open(self.path, 'w').write('\n'.join(data))


class DefaultValue(object):
    def __init__(self, conf, name, additional=None):
        self.conf = conf
        self.name = name
        self.additional = additional

    @property
    def value(self):
        try:
            return self._value
        except AttributeError:
            pass

        default_value = self.conf[self.name]
        if isinstance(default_value, dict):
            value = DefaultDictValue(default_value, self.additional)
        elif isinstance(default_value, list):
            value = DefaultListValue(default_value, self.additional)
        else:
            raise Exception('Unsupported default type: ' + str(type(default_value)))

        self._value = value
        return value

    def __iter__(self):
        return self.value.__iter__()

    def __add__(self, x):
        return DefaultValue(self.conf, self.name, x)

    def __getitem__(self, name):
        return self.value[name]

    def __contains__(self, name):
        return name in self.value

    def __setitem__(self, name, value):
        self.value[name] = value

    def __repr__(self):
        if self.additional is None:
            return "default['%s']" % self.name
        else:
            return "default['%s'] + %s" % (self.name, repr(self.additional))

class DefaultListValue(object):
    def __init__(self, default, x):
        self.default = default + x

    def __iter__(self):
        return iter(self.default)


class DefaultDictValue(object):
    def __init__(self, default, x):
        self.default = default.copy()
        self.default.update(x)
        self.additional = x

    def __getitem__(self, name):
        return self.default[name]

    def __contains__(self, name):
        return name in self.default

    def __setitem__(self, name, value):
        self.additional[name] = value
        self.default[name] = value

    def __iter__(self):
        return iter(self.default)


class DefaultValuesProvider(object):
    def __init__(self, conf):
        self.conf = conf

    def __getitem__(self, name):
        return DefaultValue(self.conf, name)


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
