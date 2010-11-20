author = 'Anton Bobrov<bobrov@vl.ru>'
name = 'Spell check'
desc = 'Attaches spell checker to current editor'

import weakref
import glib

attached_spells = weakref.WeakKeyDictionary()

def init(manager):
    manager.add_shortcut('toggle-spell-check', 'F7', 'Edit', 'Toggle spell check', toggle_spell)

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
