import os

from uxie.utils import join_to_file_dir
from uxie.misc import BuilderAware

def select_session():
    dialog = SessionSelector().dialog
    response = dialog.run()
    result = dialog.selected_session if response == 1 else None
    dialog.destroy()
    return result

class SessionSelector(BuilderAware):
    def __init__(self):
        BuilderAware.__init__(self, join_to_file_dir(__file__, 'select_session.glade'))

        from snaked.core.prefs import get_settings_path

        self.dialog.vbox.remove(self.dialog.action_area)
        self.dialog.set_default_response(1)

        for p in os.listdir(get_settings_path('')):
            if p.endswith('.session'):
                self.sessions.append((p.rpartition('.')[0],))

    def on_row_activated(self, view, path, *args):
        self.dialog.selected_session = self.sessions[path][0]
        self.dialog.response(1)