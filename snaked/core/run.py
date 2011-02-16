from optparse import OptionParser
import os

def select_session():
    import gtk
    from snaked.util import join_to_file_dir
    from snaked.core.prefs import get_settings_path

    builder = gtk.Builder()
    builder.add_from_file(join_to_file_dir(__file__, 'gui', 'select_session.glade'))
    dialog = builder.get_object('dialog')
    dialog.vbox.remove(dialog.action_area)
    dialog.set_default_response(1)

    sessions_view = builder.get_object('sessions_view')
    sessions = builder.get_object('sessions')

    for p in os.listdir(get_settings_path('')):
        if p.endswith('.session'):
            sessions.append((p.rpartition('.')[0],))

    def row_activated(view, path, *args):
        dialog.response(path[0])

    sessions_view.connect('row-activated', row_activated)

    response = dialog.run()
    result = sessions[response][0] if response >= 0 else None
    dialog.destroy()
    return result

def get_manager():
    parser = OptionParser()
    parser.add_option('-s', '--session', dest='session',
        help="Open snaked with specified session", default='default')
    parser.add_option('', '--select-session', action="store_true", dest='select_session',
        help="Show dialog to select session at startup", default=False)

    options, args = parser.parse_args()
    if options.select_session:
        options.session = select_session()

    from .app import is_master, serve

    master, conn = is_master(options.session)
    if master:
        import gobject
        gobject.threads_init()
        from .tabbed import TabbedEditorManager

        manager = TabbedEditorManager(options.session)
        opened_files = []

        session_files = filter(os.path.exists, manager.snaked_conf['OPENED_FILES'])
        active_file = manager.snaked_conf['ACTIVE_FILE']

        #open the last file specified in args, if any
        active_file = ( args and args[-1] ) or active_file

        editor_to_focus = None
        for f in session_files + args:
            f = os.path.abspath(f)
            if f not in opened_files and (not os.path.exists(f) or os.path.isfile(f)):
                e = manager.open(f)
                if f == active_file:
                    editor_to_focus = e
                opened_files.append(f)

        if not manager.editors:
            import snaked.core.quick_open
            snaked.core.quick_open.quick_open(manager.get_fake_editor())

        if editor_to_focus and active_file != opened_files[-1]:
            manager.focus_editor(editor_to_focus)

        serve(manager, conn)

        return manager
    else:
        conn.send(['OPEN'] + list(map(os.path.abspath, args)))
        conn.send(['END'])
        conn.close()
        return None

def run():
    manager = get_manager()
    if not manager:
        return

    import gtk

    try:
        gtk.main()
    except KeyboardInterrupt:
        manager.quit(None)
