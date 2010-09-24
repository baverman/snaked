import gtk
import sys

from .editor import EditorManager

def run():
    manager = EditorManager()

    filename = sys.argv[1] if len(sys.argv) > 1 else None
        
    manager.open(filename)
    
    gtk.main()
