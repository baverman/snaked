from optparse import OptionParser
import os
import glib

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

    distant = False
    FIFO = '/tmp/snaked.io.%s'%options.session
    fifo_start = '00005'

    if os.path.exists(FIFO):
        try:
            fd = open(FIFO, 'w+')
            fd.write('%s%04d\n'%(fifo_start, len(args)))
            distant = True
            out_descr = fd
        except Exception, e:
            print "Error opening socket: %r"%(e)
            try:
                os.unlink(FIFO)
            except OSError:
                pass

    if distant:
        if not args:
            print "Snaked (%s) is already running !\nIf not try to remove %s"%(options.session, FIFO)
            raise SystemExit(1)
        print "Transmitting file information to snaked"
        for fname in args:
            msg = "FILE:%s\n"%os.path.abspath(fname)
            out_descr.write('%05d%s'%(len(msg), msg))
        raise SystemExit()
    else:
        os.mkfifo(FIFO)
        out_descr = open(FIFO, 'r+')

    import gobject
    gobject.threads_init()
    from .tabbed import TabbedEditorManager

    if options.select_session:
        options.session = select_session()

    manager = TabbedEditorManager(options.session)

    opened_files = []

    session_files = []
    active_file = None

    session_files = manager.snaked_conf['OPENED_FILES']
    active_file = manager.snaked_conf['ACTIVE_FILE']

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

    if not distant:
        import atexit
        def remove_socket(fd, fname):
            fd.close()
            os.unlink(fname)

        atexit.register(remove_socket, out_descr, FIFO)

        def file_injector(fd, flag):
            sz = int(fd.read(5))
            count = int(fd.read(sz))
            for n in xrange(count):
                sz = int(fd.read(5))
                data = fd.read(sz)
                if data.startswith('FILE:'):
                    fname = data[5:-1]
                    if fname not in opened_files: # FIXME: this is unreliable, is there some list in manager ?
                        manager.open(fname)
                        opened_files.append(fname)
                else:
                    print "Unknown descriptor"
            return True
        glib.io_add_watch(out_descr, glib.IO_IN|glib.IO_HUP, file_injector)
    return manager

def run():
    manager = get_manager()

    import gtk

    try:
        gtk.main()
    except KeyboardInterrupt:
        manager.quit(None)
