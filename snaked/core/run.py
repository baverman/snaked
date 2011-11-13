from optparse import OptionParser
import os

from snaked import VERSION

def get_manager():
    parser = OptionParser(version='%prog ' + VERSION)
    parser.add_option('-s', '--session', dest='session',
        help="Open snaked with specified session", default='default')
    parser.add_option('', '--select-session', action="store_true", dest='select_session',
        help="Show dialog to select session at startup", default=False)
    parser.add_option('-d', '--debug', action="store_true", dest='debug',
        help="Run embedded drainhunter", default=False)
    parser.add_option('', '--g-fatal-warnings', action="store_true")

    options, args = parser.parse_args()
    if options.select_session:
        from snaked.core.gui import session_selector
        options.session = session_selector.select_session()

    from .app import is_master, serve

    master, conn = is_master(options.session)
    if master:
        import gobject
        gobject.threads_init()
        from .manager import EditorManager

        manager = EditorManager(options.session)
        manager.start(args)
        serve(manager, conn)

        if options.debug:
            import drainhunter.server
            drainhunter.server.run()

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
        manager.quit()
