import os
import shutil
from os.path import join, dirname, realpath, abspath, exists, expanduser

import gobject
import gtk

from snaked.signals.signals import Handler
from snaked.signals import weak_connect

def idle_callback(callable, args):
    args, kwargs = args
    callable(*args, **kwargs)
    return False

def idle(callable, *args, **kwargs):
    options = {}
    if 'priority' in kwargs:
        options['priority'] = kwargs['priority']
        del kwargs['priority']
    return gobject.idle_add(idle_callback, callable, (args, kwargs), **options)

def save_file(filename, data, encoding, keep_tmp=False):
    tmpfilename = realpath(filename) + '.bak'

    try:
        f = open(tmpfilename, 'w')
    except IOError:
        dname = dirname(tmpfilename)
        if not exists(dname):
            os.makedirs(dname, mode=0755)
            f = open(tmpfilename, 'w')
        else:
            raise

    f.write(data.encode(encoding))
    f.close()

    if exists(filename):
        try:
            shutil.copymode(filename, tmpfilename)
        except OSError:
            pass

    if keep_tmp:
        return tmpfilename
    else:
        os.rename(tmpfilename, filename)

def connect(sender, signal, obj, attr, idle=False, after=False):
    return Handler(weak_connect(
        sender, signal, obj, attr, idle=idle, after=after), sender)

def join_to_file_dir(filename, *args):
    return join(dirname(filename), *args)

def join_to_settings_dir(*args):
    config_dir = os.getenv('XDG_CONFIG_HOME', expanduser('~/.config'))
    return join(config_dir, 'snaked', *args)

def join_to_cache_dir(*args):
    config_dir = os.getenv('XDG_CACHE_HOME', expanduser('~/.cache'))
    return join(config_dir, 'snaked', *args)

def make_missing_dirs(filename):
    path = dirname(filename)
    if not exists(path):
        os.makedirs(path, mode=0755)

def get_project_root(filename):
    path = dirname(abspath(filename))
    magic_pathes = ['.git', '.hg', '.bzr', '.ropeproject', '.snaked_project']

    while True:
        if any(exists(join(path, p)) for p in magic_pathes):
            return path

        parent = dirname(path)
        if parent == path:
            return None

        path = parent

def open_mime(filename):
    import subprocess
    subprocess.Popen(['/usr/bin/env', 'xdg-open', filename]).poll()


def refresh_gui():
    while gtk.events_pending():
        gtk.main_iteration_do(block=False)

def single_ref(func):
    real_name = '__' + func.__name__
    holder_name = func.__name__ + '_holder'

    def inner(self):
        try:
            return getattr(self, real_name)
        except AttributeError:
            pass

        cls = self.__class__
        if not hasattr(cls, holder_name) or not getattr(cls, holder_name)():
            import weakref
            var = func(self)
            setattr(cls, holder_name, weakref.ref(var))

        setattr(self, real_name, getattr(cls, holder_name)())
        return getattr(self, real_name)

    return property(inner)

def lazy_property(func):
    real_name = '__' + func.__name__

    def inner(self):
        try:
            return getattr(self, real_name)
        except AttributeError:
            pass

        var = func(self)
        setattr(self, real_name, var)
        return var

    return property(inner)

def set_activate_the_one_item(entry, treeview):
    def activate(*args):
        if len(treeview.get_model()) == 1:
            treeview.set_cursor((0,))
            treeview.row_activated((0,), treeview.get_column(0))

    entry.connect('activate', activate)

def mimic_to_sourceview_theme(textview, sourceview):
    """Gets font and bg settings from gtksourceview and applies it to textview

    :type textview: gtk.TextView()
    :type sourceview: gtksourceview2.View()

    """

    style = sourceview.get_buffer().get_style_scheme().get_style('text')
    if style:
        if style.props.background_set:
            textview.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(style.props.background))
        if style.props.foreground_set:
            textview.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(style.props.foreground))

    style = sourceview.get_buffer().get_style_scheme().get_style('selection')
    if style:
        if style.props.background_set:
            textview.modify_base(gtk.STATE_SELECTED, gtk.gdk.color_parse(style.props.background))
        if style.props.foreground_set:
            textview.modify_text(gtk.STATE_SELECTED, gtk.gdk.color_parse(style.props.foreground))


class BuilderAware(object):
    def __init__(self, glade_file):
        self.gtk_builder = gtk.Builder()
        self.gtk_builder.add_from_file(glade_file)
        self.gtk_builder.connect_signals(self)

    def __getattr__(self, name):
        obj = self.gtk_builder.get_object(name)
        if not obj:
            raise AttributeError('Builder have no %s object' % name)

        setattr(self, name, obj)
        return obj