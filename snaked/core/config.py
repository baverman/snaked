import prefs

class SnakedConf(prefs.PySettings):
    LAST_POSITION = None
    LAST_POSITION_DOC = 'Tuple of ((x,y), (w,h)) last window position'

    FULLSCREEN = False
    FULLSCREEN_DOC = 'State of fullscreen mode'

    OPENED_FILES = []
    OPENED_FILES_DOC = 'Last opened files'

    ACTIVE_FILE = ''
    ACTIVE_FILE_DOC = 'Last active file'

    PANEL_HEIGHT = 200
    PANEL_HEIGHT_DOC = "Console, test and other panels height"
