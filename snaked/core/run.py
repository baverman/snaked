from optparse import OptionParser
import sys
import os

def get_manager():
    parser = OptionParser()
    parser.add_option('-s', '--session', dest='session', help="Open snaked with specified session")
    parser.add_option('-w', '--windowed', action="store_true", 
        dest='windowed', default = False, help="Open separate editor window instead tab")
    options, args = parser.parse_args()

    import gobject
    gobject.threads_init()
    
    if options.windowed:
        from .windowed import WindowedEditorManager as WM
    else:
        from .tabbed import TabbedEditorManager as WM

    manager = WM()

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
        print >> sys.stderr, 'You must specify at least one file to edit'
        sys.exit(1)

    if editor_to_focus and active_file != opened_files[-1]:
        manager.focus_editor(editor_to_focus)
        
    return manager
            
def run():
    manager = get_manager()

    import gtk
    
    try:    
        gtk.main()
    except KeyboardInterrupt:
        manager.quit()
