def get_manager():
    from optparse import OptionParser
    import sys
    
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

    if options.session:
        manager.open_session(options.session)
    
    for f in args:    
        manager.open(f)

    if not manager.editors:
        print >> sys.stderr, 'You must specify at least one file to edit'
        sys.exit(1)
        
    return manager
            
def run():
    manager = get_manager()

    import gtk
    
    try:    
        gtk.main()
    except KeyboardInterrupt:
        manager.quit()
