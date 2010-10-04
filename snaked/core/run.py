def run():
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('-s', '--session', dest='session', help="Open snaked with specified session")
    options, args = parser.parse_args()

    import gtk
    import gobject
    gobject.threads_init()
    
    from .tabbed import TabbedEditorManager

    manager = TabbedEditorManager()

    if options.session:
        manager.open_session(options.session)
    else:
        if len(args):
            for f in args:    
                manager.open(f)
        else:
            manager.open(None)
    
    gtk.main()
