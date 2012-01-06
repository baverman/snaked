author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'External tools'
desc = 'Allows one to define own commands'

from uxie.utils import lazy_func

def init(injector):
    injector.bind('editor', 'external-tools-default-config', 'Prefs/Global/_Tools',
        lazy_func('.plugin.edit_external_tools'), 'global')

    injector.bind('editor', 'external-tools-session-config', 'Prefs/Session/_Tools',
        lazy_func('.plugin.edit_external_tools'), 'session')

    injector.bind_dynamic('editor', 'external-tools', '_Run/external-tools',
        lazy_func('.plugin.generate_menu'), lazy_func('.plugin.resolve_menu_entry'))

    injector.bind_menu('Run').to('<Alt>X')

