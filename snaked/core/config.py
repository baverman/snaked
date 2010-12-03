import prefs

class SnakedConf(prefs.PySettings):
    DISABLE_LEFT_CLICK = False
    DISABLE_LEFT_CLICK_DOC = 'Disable left mouse button handling in editor view'

    RESTORE_POSITION = True
    RESTORE_POSITION_DOC = 'Restore snaked window position'

    LAST_POSITION = None
    LAST_POSITION_DOC = 'Tuple of ((x,y), (w,h)) last window position'

    FULLSCREEN = False
    FULLSCREEN_DOC = 'State of fullscreen mode'

    SHOW_TABS = True
    SHOW_TABS_DOC = 'State of tabs visibility'


def add_option(name, default, doc=None):
    setattr(SnakedConf, name, default)
    if doc:
        setattr(SnakedConf, name+'_doc', doc)
