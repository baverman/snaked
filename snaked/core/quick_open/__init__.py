dialog = None

def init(manager):
    manager.add_shortcut('quick-open', '<ctrl><alt>r', 'File', "Shows quick open dialog", activate)

    manager.add_global_option('QUICK_OPEN_HIDDEN_FILES',
        ['.pyc','.pyo','.svn','.git','.hg','.ropeproject','.snaked_project'],
        "Defines files to hide in quick open's browser mode")

    manager.add_global_option('QUICK_OPEN_SHOW_HIDDEN', False,
        "Option to show hidden files. <ctrl>H in quick open dialog")

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

def activate(editor):
    global dialog
    if not dialog:
        from gui import QuickOpenDialog
        dialog = QuickOpenDialog()

    dialog.show(editor)

def quit():
    global dialog
    dialog = dialog

def set_context(project_root, contexts):
    import settings
    settings.ignore_contexts[project_root] = contexts
