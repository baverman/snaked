Plugins
=======

.. _complete_words:

Complete words
--------------

Similar to Eclipse behavior: cycles through possible word completions from
opened documents.

Default key: ``<alt>slash``


.. _edit_and_select:

Edit and Select
---------------

Provides features for easy text editing.

* ``<ctrl>d`` deletes line under cursor with copying it into clipboard.

* ``<ctrl><alt>o`` shows cursor offset and cursor column position.
  Huh? Simply I need offset when write tests (parsing, code analyzing, etc.).

* ``<alt>w`` smart select. Selects semantic blocks. Just try it. Have you ever
  need to select whole function definition or string in quotes or function
  parameters or function call with parameters or statement block? There is only
  one function for such tasks in Snaked. In conjunction with stock
  gtksourceview2 selection moving (``<alt>Up``, ``<alt>Down``) it allows forget
  about copy-paste.

* ``<alt>f`` reformats selection to current right margin width.

That's all for now. Planed feature functionality:

* Smart string literals edit.

* Automatic brackets and quotes pairing.

* Automatic text wrap.

* Maybe vertical selection.

* Vim-like numbers incrementing/decrementing (``<ctrl>a``, ``<ctrl>x``).

* Vim-like above line symbols copying (``<ctrl>y``).

* Vim-like... Over 9000 other features. In order of first need. Maybe implement
  vim mode? Damn.


Goto Dir
--------

Default shortcut ``<crtl><alt>l`` opens editor file directory in file manager.


Goto Line
---------

``<ctrl>l`` popups dialog with line number input.


Hash Comment
------------

Comments and uncomments code with hashes. Useful for languages with appropriate
comment symbols. Default key ``<ctrl>slash``.


Python Flakes
-------------

Background python code linter. Highlights problems like unused or undefined
imports or variables. Also gives feedback about syntax errors. Quite handy
plugin.


Save positions
--------------

Remembers current file position on editor close and restores it on open.


Search
------

Simply search, like in other editors.

.. image:: /images/search.*


Replace entry supports back references (``\1`` or ``\g<name>``) for regular
expression groups in search field.

Shortcuts
*********

* ``<ctrl>f`` shows dialog.

* ``Escape`` hides it.

* ``Enter`` in search or replace text entry do actual searching.

* ``<ctrl>j``, ``<ctrl>k`` navigate to next/previous match.

* ``<ctrl>h`` highlights selection occurrences.

To control `ignore case`, `regex` checkboxes and activate `Replace`/`Replace
all` buttons you can use mnemonics: ``<alt>c``, ``<alt>x``, ``<alt>p`` and
``<alt>a``.


.. _external-tools:

External tools
--------------

Plugin allows to run commands optionally piping selection or whole buffer's
content to it and process it's stdout.

.. image:: /images/external-tools.*


* ``Name``: tool's name. You can use underscore ("_") to define mnemonic key and
  pango markup.

* ``Langs``: comma separated list of languages for which this tool is intended.
  Leave field empty if tool should be available in all editors.

* ``Command``: Shell command to execute. Following variables are supported:

  * ``%f`` — current filename
  * ``%d`` — current filename's directory
  * ``%p`` — current project directory

  Take note, you have not to quote it.

* ``Stdin`` and ``Stdout`` should be self-explanatory.

Default key to activate run menu is ``<alt>x``. Actual tool can be run by
pressing it's mnemonic key or selecting it with cursor keys an hitting
``Enter``.
