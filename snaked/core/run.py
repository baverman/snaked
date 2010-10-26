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
    parser.add_option('-s', '--session', dest='session', help="Open snaked with specified session")
    parser.add_option('-w', '--windowed', action="store_true", 
        dest='windowed', default=False, help="Open separate editor window instead tab")
    parser.add_option('', '--select-session', action="store_true", dest='select_session',
        help="Opens dialog to select session", default=False)
    parser.add_option('', '--hide-tabs', action="store_false", dest='show_tabs',
        help="Hides tabs in tabbed interface", default=True)

    options, args = parser.parse_args()

    import gobject
    gobject.threads_init()
    
    if options.windowed:
        from .windowed import WindowedEditorManager as WM
        manager = WM()
    else:
        from .tabbed import TabbedEditorManager as WM
        manager = WM(options.show_tabs)

    if options.select_session:
        options.session = select_session()

    opened_files = []
    
    session_files = []
    active_file = None
    if options.session:
        settings = manager.get_session_settings(options.session)
        session_files = settings.get('files', [])
        active_file = settings.get('active_file', None)
        manager.session = options.session
    
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
        snaked.core.quick_open.activate(manager.get_fake_editor())

    if editor_to_focus and active_file != opened_files[-1]:
        manager.focus_editor(editor_to_focus)
        
    return manager
            
def run():
    manager = get_manager()

    import gtk
    
    try:    
        gtk.main()
    except KeyboardInterrupt:
        manager.quit(None)
