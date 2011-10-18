import os.path

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

        cfg = get_settings_path('')
        for p in os.listdir(cfg):
            if os.path.isdir(os.path.join(cfg, p)):
                self.sessions.append((p,))

    def on_row_activated(self, view, path, *args):
        self.dialog.selected_session = self.sessions[path][0]
        self.dialog.response(1)