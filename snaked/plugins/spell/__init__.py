author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Spell check'
desc = 'Attaches spell checker to current editor'

import weakref
import glib
import gtk

attached_spells = weakref.WeakKeyDictionary()

def init(manager):
    manager.add_shortcut('toggle-spell-check', 'F7', 'Edit', 'Toggle spell check', toggle_spell)

    manager.add_editor_preferences(
        on_preferences_dialog_created,
        on_preferences_dialog_refresh, {
        'default':{
            'spell-check': False
        }
    })

def editor_opened(editor):
    if editor.prefs['spell-check']:
        toggle_spell(editor)

def on_preferences_dialog_created(dialog):
    """:type dialog: snaked.core.gui.editor_prefs.PreferencesDialog"""
    dialog.spell_check = gtk.CheckButton('Spell chec_k')
    dialog.spell_check.connect('toggled', dialog.on_checkbox_toggled, 'spell-check')
    dialog.spell_check.show()

    dialog.vbox.pack_start(dialog.spell_check, False, False)

def on_preferences_dialog_refresh(dialog, pref):
    """:type dialog: snaked.core.gui.editor_prefs.PreferencesDialog"""
    dialog.spell_check.set_active(pref['spell-check'])

def toggle_spell(editor):
    if editor in attached_spells:
        spell = attached_spells[editor]
        spell.detach()
        del attached_spells[editor]
    else:
        try:
            from gtkspell import Spell
            from locale import getdefaultlocale
            attached_spells[editor] = Spell(editor.view, getdefaultlocale()[0])
        except ImportError:
            editor.message('Spellcheck not available. You need to install pygtkspell')
        except glib.GError:
            editor.message('Spellcheck not available. Perhaps you have no dictionaries')
