import weakref

editors = weakref.WeakKeyDictionary()
dialog = [None]

def init(manager):
    """:type manager:snaked.core.plugins.ShortcutsHolder"""

    manager.add_shortcut('show-editor-list', '<alt>e', 'Window',
        'Show editor list', show_editor_list)

def editor_created(editor):
    editors[editor] = True

def editor_closed(editor):
    try:
        del editors[editor]
    except KeyError:
        pass

def show_editor_list(editor):
    if not dialog[0]:
        from gui import EditorListDialog
        dialog[0] = EditorListDialog()

    dialog[0].show(editor, editors)