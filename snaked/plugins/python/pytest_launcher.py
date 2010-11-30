import sys
import os.path
import time

def run_test(project_dir, match=None, files=[]):
    from subprocess import Popen
    from multiprocessing.connection import Client, arbitrary_address

    addr = arbitrary_address('AF_UNIX')
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'launcher/pt.py')

    args = [sys.executable, filename, addr, '-q']
    if match:
        args.append('-k %s' % match)

    args.extend(files)
    proc = Popen(args, cwd=project_dir)
    start = time.time()
    while not os.path.exists(addr):
        if time.time() - start > 5:
            raise Exception('py.test launching timeout exceed')
        time.sleep(0.01)

    conn = Client(addr)

    return proc, conn