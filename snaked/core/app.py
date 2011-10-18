import sys, os, time
import socket
from multiprocessing.connection import Client, Listener
import multiprocessing.connection

def _init_timeout(timeout=3):
    return time.time() + timeout

def get_addr(session):
    if sys.platform == 'win32':
        return '\\.\pipe\snaked.session.%s.%s' % (os.environ.get('USERNAME', 'USERNAME'), session)
    else:
        return '/tmp/snaked.session.%i.%s' % (os.geteuid(), session)

def is_master(session):
    addr = get_addr(session)
    try:
        return True, Listener(addr)
    except socket.error:
        multiprocessing.connection._init_timeout = _init_timeout
        i = 2
        while i > 0:
            try:
                conn = Client(addr)
                return False, conn
            except socket.error, e:
                print e

            time.sleep(0.1)
            i -= 1

        os.remove(addr)
        return is_master(session)

def serve(manager, listener):
    def runner():
        while True:
            conn = listener.accept()
            conn_alive = True
            while conn_alive:
                while conn.poll():
                    try:
                        data = conn.recv()
                        if data[0] == 'END':
                            conn_alive = False
                        elif data[0] == 'OPEN':
                            for f in data[1:]:
                                manager.open_or_activate(f)
                            [w for w in manager.windows if w][0].present()
                    except EOFError:
                        break
                    except Exception:
                        import traceback
                        traceback.print_exc()

                time.sleep(0.1)

    def on_quit():
        listener.close()

    manager.on_quit.append(on_quit)

    import threading
    t = threading.Thread(target=runner)
    t.daemon = True
    t.start()
