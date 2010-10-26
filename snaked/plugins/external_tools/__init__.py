author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'External tools'
desc = 'Allows one to define own commands'

from snaked.core.prefs import register_dialog

def init(manager):
    manager.add_shortcut('external-tools', '<alt>x', 'Tools', 'Run tool', run_tool)
    register_dialog('External tools', show_preferences, 'run', 'external', 'tool', 'command')

def run_tool(editor):
    pass
    
def show_preferences(editor):
    from prefs import PreferencesDialog
    PreferencesDialog().show(editor)