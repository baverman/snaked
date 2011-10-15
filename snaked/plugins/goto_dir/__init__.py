author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Goto dir'
desc = "Opens file's directory"

def init(injector):
    injector.bind_accel('editor-active', 'goto-dir', '_File/Open file\'s directory',
        '<ctrl><alt>l', goto_dir)

def goto_dir(editor):
    import gio
    import os.path

    f = gio.file_parse_name(os.path.dirname(editor.uri))
    ct = f.query_info(gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE).get_content_type()
    ai = gio.app_info_get_default_for_type(ct, False)

    if ai:
        ai.launch([f])
        editor.message('File manager started', 1000)
    else:
        editor.message('Unknown content type for launch %s' % ct)
