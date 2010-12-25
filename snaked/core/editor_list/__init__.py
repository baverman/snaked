import weakref

editors = weakref.WeakKeyDictionary()
dialog = [None]
recent_editors = {}

def init(manager):
    """:type manager:snaked.core.plugins.ShortcutsHolder"""

    manager.add_shortcut('show-editor-list', '<alt>e', 'Window',
        'Show editor list', show_editor_list)

    manager.add_global_option('EDITOR_LIST_SWITCH_ON_SELECT', True,
        'Activates editor on item select (i.e cursor move) in editor list dialog')

def editor_created(editor):
    editors[editor] = True

def editor_closed(editor):
    try:
        del editors[editor]
    except KeyError:
        pass

    recent_editors[editor.uri] = editor.get_title.emit()

def show_editor_list(editor):
    if not dialog[0]:
        from gui import EditorListDialog
        dialog[0] = EditorListDialog()

    dialog[0].show(editor, editors, recent_editors)
