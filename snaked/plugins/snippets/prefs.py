import weakref

from snaked.util import BuilderAware, join_to_file_dir, idle, set_activate_the_one_item
from snaked.util import make_missing_dirs, join_to_settings_dir

def on_snippet_saved(editor, ctx):
    from . import existing_snippet_contexts, load_snippets_for

    existing_snippet_contexts[ctx] = editor.uri
    load_snippets_for(ctx)

    editor.message('Snippets were updated')


class PreferencesDialog(BuilderAware):
    """glade-file: prefs.glade"""

    def __init__(self, existing_snippets):
        BuilderAware.__init__(self, join_to_file_dir(__file__, 'prefs.glade'))

        from snaked.core.shortcuts import ShortcutActivator
        self.activator = ShortcutActivator(self.window)
        self.activator.bind('Escape', self.hide)
        self.activator.bind('<alt>s', self.focus_search)
        self.existing_snippets = existing_snippets

        set_activate_the_one_item(self.search_entry, self.snippets_view)

    def hide(self):
        self.window.destroy()

    def show(self, editor):
        self.editor = weakref.ref(editor)
        self.fill_snippets(None)
        editor.request_transient_for.emit(self.window)
        self.window.show()

    def fill_snippets(self, search):
        self.snippets.clear()
        for name in sorted(self.existing_snippets):
            if not search or search in name:
                self.snippets.append((name,))

    def on_delete_event(self, *args):
        return False

    def on_search_entry_changed(self, *args):
        search = self.search_entry.get_text().strip().lower()
        idle(self.fill_snippets, search)

    def activate(self, *args):
        (model, iter) = self.snippets_view.get_selection().get_selected()
        if iter:
            name = model.get_value(iter, 0)
            self.edit_context(name)
        else:
            self.editor().message('You need select item')

    def focus_search(self):
        self.search_entry.grab_focus()

    def edit_context(self, ctx):
        user_snippet_filename = join_to_settings_dir('snippets', ctx + '.snippets')
        if ctx in self.existing_snippets and \
                self.existing_snippets[ctx] != user_snippet_filename:

            import shutil
            make_missing_dirs(user_snippet_filename)
            shutil.copy(self.existing_snippets[ctx], user_snippet_filename)

        idle(self.hide)
        e = self.editor().open_file(user_snippet_filename)
        e.connect('file-saved', on_snippet_saved, ctx)

    def on_create_snippet_activate(self, button):
        ctx = self.search_entry.get_text()
        if ctx:
            self.edit_context(ctx)
        else:
            self.editor().message('Enter snippet name in search entry', 3000)