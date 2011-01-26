import os, time
import socket
from multiprocessing.connection import Client, Listener, arbitrary_address
import multiprocessing.connection

def _init_timeout(timeout=3):
    return time.time() + timeout

def create_master_listener(fd):
    addr = arbitrary_address('AF_UNIX')
    os.write(fd, addr)
    os.close(fd)

    return Listener(addr)

def is_master(session):
    # Ahtung! Possible races, for example on opening multiple files from file browser.
    filename = '/tmp/snaked.session.%i.%s' % (os.geteuid(), session)
    try:
        fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        return True, create_master_listener(fd)
    except OSError:
        multiprocessing.connection._init_timeout = _init_timeout
        i = 2
        while i > 0:
            try:
                conn = Client(open(filename).read())
                return False, conn
            except socket.error:
                pass

            time.sleep(0.1)
            i -= 1

        fd = os.open(filename, os.O_WRONLY | os.O_CREAT)
        return True, create_master_listener(fd)

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
                                manager.open(f)
                            manager.activate_main_window()
                    except EOFError:
                        break
                    except Exception:
                        import traceback
                        traceback.print_exc()

                time.sleep(0.1)

    def on_quit():
        listener.close()
        try:
            os.unlink('/tmp/snaked.session.' + manager.session)
        except:
            pass

    manager.on_quit.append(on_quit)

    import threading
    t = threading.Thread(target=runner)
    t.daemon = True
    t.start()
