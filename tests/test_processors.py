# -*- coding: utf-8 -*-

import gtk

from snaked.core.processors import remove_trailing_spaces

def test_remove_trailing_spaces():
    buffer = gtk.TextBuffer()
    buffer.set_text(u"   \nword слово   \t  \n   \t \n\n   word  слово      """)

    remove_trailing_spaces(buffer)
    text = buffer.get_text(*buffer.get_bounds()).decode('utf-8')
    assert text == u"\nword слово\n\n\n   word  слово"
