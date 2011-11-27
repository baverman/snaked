from bisect import bisect
import gtk

from uxie.complete import TextViewCompleter

completer = None

def init(injector):
    injector.bind('textview-active', 'complete', 'Edit/Complete', complete)

def complete(textview):
    if not hasattr(textview, 'completer'):
        textview.get_toplevel().message('Where is your attached completer now?',
            'warn', parent=textview)
        return

    textview.completer.complete(textview)

def add_completion_provider(buf, provider, priority=None):
    if priority is None:
        priority = 0

    value = (-priority, provider)
    if not hasattr(buf, 'completion_providers'):
        buf.completion_providers = []

    buf.completion_providers.insert(bisect(buf.completion_providers, value), value)

def create_completer():
    model = gtk.ListStore(object, str, object, bool) # provider, match, object, selection
    view = gtk.TreeView(model)
    view.set_headers_visible(False)
    view.append_column(gtk.TreeViewColumn('None', gtk.CellRendererText(),
        markup=1, sensitive=3))

    view.get_selection().set_select_function(lambda info: model[info[0]][3])

    return TextViewCompleter(view)

def get_completer():
    global completer
    if not completer:
        completer = create_completer()

    return completer

def fill_callback(view, textview, check, providers=None, it=None):
    buf = textview.get_buffer()
    model = view.get_model()
    model.clear()

    is_interactive = it is None

    it = it or buf.get_iter_at_mark(buf.get_insert())
    providers = providers or (r[1] for r in buf.completion_providers)
    provider_iters = []
    for provider in providers:
        if is_interactive:
            ctx = provider.is_match(it.copy())
        else:
            ctx = it.copy()

        if ctx is not None:
            is_any_items = False
            for name, obj in provider.complete(ctx, is_interactive):
                next(check)
                start_iter = model.append((provider, name, obj, True))
                if not is_any_items:
                    provider_iters.append((provider, start_iter))
                    is_any_items = True

    if len(provider_iters) > 1:
        for p, it in provider_iters:
            model.insert_before(it, (None, '<b>%s</b>' % p.get_name(), None, False))

def activate_callback(view, path, textview, is_final):
    if is_final:
        provider, _, obj = tuple(view.get_model()[path])[:3]
        provider.activate(textview, obj)

def attach_completer(textview):
    completer = get_completer()
    completer.attach(textview, fill_callback, activate_callback)
    textview.completer = completer


class Provider(object):
    def is_match(self, it):
        return None

    def complete(self, ctx, is_interactive):
        return []

    def get_name():
        return 'Unknown'

    def activate(self, textview, obj):
        pass
