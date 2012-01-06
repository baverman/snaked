dialog = [None]
recent_editors = {}

def init(injector):
    from ..prefs import add_option

    add_option('EDITOR_LIST_SWITCH_ON_SELECT', True,
        'Activates editor on item select (i.e cursor move) in editor list dialog')

    injector.bind('window', 'show-editor-list', 'Window/_Editor list#20',
        show_editor_list).to('<alt>e')

    injector.on_done('last-buffer-editor', editor_closed)

def editor_closed(editor):
    recent_editors[editor.uri] = editor.get_title.emit()

def show_editor_list(window):
    if not dialog[0]:
        from .gui import EditorListDialog
        dialog[0] = EditorListDialog()

    dialog[0].show(window, recent_editors)
