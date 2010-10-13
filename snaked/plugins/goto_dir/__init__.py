author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Goto dir'
desc = "Opens file's directory"

def init(manager):
    manager.add_shortcut('goto-dir', '<ctrl><alt>l', 'File', "Opens file's directory", goto_dir)
    
def goto_dir(editor):
    import subprocess
    import os.path
    
    subprocess.Popen(['/usr/bin/env', 'xdg-open', os.path.dirname(editor.uri)]).poll()
    editor.message('File manager started', 1000)