def profiled():
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('-s', '--session', dest='session', help="Open snaked with specified session")
    options, args = parser.parse_args()

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
    
def run():

    #import cProfile
    
    #cProfile.runctx('profiled()', {'profiled':profiled}, None, '/tmp/wow.prof')
    
    profiled()

    import gtk    
    gtk.main()
