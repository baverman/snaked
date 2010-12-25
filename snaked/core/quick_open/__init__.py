dialog = [None]

def init(manager):
    manager.add_shortcut('quick-open', '<ctrl><alt>r', 'File', "Show quick open dialog", quick_open)
    manager.add_shortcut('slow-open', '<ctrl>F12', 'File', "Show standard open dialog", slow_open)

    manager.add_global_option('QUICK_OPEN_HIDDEN_FILES',
        ['.pyc','.pyo','.svn','.git','.hg','.ropeproject','.snaked_project'],
        "Defines files to hide in quick open's browser mode")

    manager.add_global_option('QUICK_OPEN_SHOW_HIDDEN', False,
        "Option to show hidden files. <ctrl>H in quick open dialog")

    manager.add_global_option('QUICK_OPEN_RECENT_PROJECTS', [],
        "Recent projects be shown in quick open dialog")

    manager.add_context('quick_open', set_context)

def editor_opened(editor):
    import settings
    root = editor.project_root
    if root and root not in settings.recent_projects:
        settings.recent_projects.append(root)

    if not root:
        root = editor.get_project_root(larva=True)
        if root and root not in settings.larva_projects:
            settings.larva_projects.append(root)

def quick_open(editor):
    if not dialog[0]:
        from gui import QuickOpenDialog
        dialog[0] = QuickOpenDialog()

    dialog[0].show(editor)

def slow_open(editor):
    import gtk
    import os.path

    dialog = gtk.FileChooserDialog("Open file...",
        None,
        gtk.FILE_CHOOSER_ACTION_OPEN,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
        gtk.STOCK_OPEN, gtk.RESPONSE_OK))

    dialog.set_default_response(gtk.RESPONSE_OK)
    dialog.set_current_folder(os.path.dirname(editor.uri))

    response = dialog.run()
    if response == gtk.RESPONSE_OK:
        editor.open_file(dialog.get_filename())

    dialog.destroy()

def quit():
    dialog[0] = None

def set_context(project_root, contexts):
    import settings
    settings.ignore_contexts[project_root] = contexts
