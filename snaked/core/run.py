def init():
    from optparse import OptionParser

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
    else:
        if len(args):
            for f in args:    
                manager.open(f)
        else:
            manager.open(None)
    
def run():

    #import cProfile
    
    #cProfile.runctx('profiled()', {'profiled':profiled}, None, '/tmp/wow.prof')
    
    init()

    import gtk    
    gtk.main()
