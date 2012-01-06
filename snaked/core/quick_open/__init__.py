dialog = [None]

def init(injector):
    from .. import prefs

    injector.bind(('window', 'editor'), 'slow-open', 'File/_Open#10', slow_open).to('<ctrl>F12')
    injector.bind('window', 'quick-open', 'File/Quic_k open', quick_open).to('<ctrl><alt>r')

    injector.on_ready('editor-with-new-buffer', editor_opened)

    prefs.add_option('QUICK_OPEN_HIDDEN_FILES',
        lambda:['.pyc','.pyo','.svn','.git','.hg','.ropeproject','.snaked_project', '__pycache__'],
        "Defines files to hide in quick open's browser mode")

    prefs.add_option('QUICK_OPEN_SHOW_HIDDEN', False,
        "Option to show hidden files. <ctrl>H in quick open dialog")

    prefs.add_internal_option('QUICK_OPEN_RECENT_PROJECTS', list,
        "Recent projects will be shown in quick open dialog")

    prefs.add_internal_option('QUICK_OPEN_CURRENT_PROJECTS', list,
        "Projects will be selected in quick open dialog")

def editor_opened(editor):
    from . import settings
    root = editor.project_root

    if root and root not in settings.recent_projects:
        settings.recent_projects.append(root)
    if not root:
        root = editor.get_project_root(larva=True)
        if root and root not in settings.larva_projects:
            settings.larva_projects.append(root)

def quick_open(window):
    if not dialog[0]:
        from .gui import QuickOpenDialog
        dialog[0] = QuickOpenDialog()

    dialog[0].show(window)

def slow_open(window, editor):
    import gtk
    import os.path

    dialog = gtk.FileChooserDialog("Open file...",
        window,
        gtk.FILE_CHOOSER_ACTION_OPEN,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
        gtk.STOCK_OPEN, gtk.RESPONSE_OK))

    dialog.set_default_response(gtk.RESPONSE_OK)
    dialog.set_current_folder(os.path.dirname(editor.uri))

    response = dialog.run()
    if response == gtk.RESPONSE_OK:
        window.manager.open_or_activate(dialog.get_filename(), window)

    dialog.destroy()

def quit():
    dialog[0] = None
