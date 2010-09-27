import gtk
import gobject
import sys

gobject.threads_init()

from .editor import EditorManager

def run():
    manager = EditorManager()

    if len(sys.argv) > 1:
        for f in sys.argv[1:]:    
            manager.open(f)
    else:
        manager.open(None)
    
    gtk.main()
