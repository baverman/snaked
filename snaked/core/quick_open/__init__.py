dialog = None
        
def init(manager):
    manager.add_shortcut('quick-open', '<ctrl><alt>r', 'File', "Shows quick open dialog", activate)

def editor_opened(editor):
    import settings
    root = editor.project_root
    if root and root not in settings.recent_projects:            
        settings.recent_projects.append(root)                
    
def activate(editor):
    global dialog
    if not dialog:
        from gui import QuickOpenDialog
        dialog = QuickOpenDialog()

    dialog.show(editor)
        
def quit():
    global dialog
    dialog = dialog
