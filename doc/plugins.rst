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

* ``<ctrl><alt>o`` shows cursor offset position. Huh? Simply I need offset
  when write tests (parsing, code analyzing, etc.).

* ``<alt>w`` smart select. Selects semantic blocks. Just try it. Have you ever
  need to select whole function definition or string in quotes or function
  parameters or function call with parameters or statement block? There is only
  one function for such tasks in Snaked. In conjunction with stock
  gtksourceview2 selection moving (``<alt>Up``, ``<alt>Down``) it allows forget
  about copy-paste.

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

Comments and uncomments code with hashes. Useful for languages with appropriate comment
symbols. Default key ``<ctrl>slash``.


Python
------

Strictly for the sake of this plugin I started Snaked's development. It features:

* Pretty editor title formating. Package modules are presented like
  `package.module` or `package` instead `module.py` or `__init__.py`. Very
  useful extension to distinguish similar file names. Must have for every
  Pytonier.

* :ref:`Goto python definition <python-goto-definition>`.

* :ref:`Code autocomplete <python-autocomplete>`

* :ref:`Outline navigation <python-outline>`

* :ref:`Type hints <python-type-hints>`. Provide rope with additional info about
  types for better inference, refactoring and code completion.


Python Flakes
-------------

Background python code linter. Highlights problems like unused or undefined imports or
variables. Also gives feedback about syntax errors. Quite handy plugin.


.. _quick-open:

Quick Open
----------

Heart of project navigation. Really quick (and responsive), I worked hard for
that. With easy project selection. It searches files only in current project
following these matching rules:

* filename starts with search term.

* filename contains search term

* file path contains search term

* fuzzy match. if search term contains slashes it matches similar file paths. For
  example ``pl/py`` will match ``plugin/python/__init__.py`` or
  ``plugin/name/python.py``

Shortcuts
*********

* ``<ctrl>Enter`` opens selected item with default system editor. This important
  feature is missed in many other editors. For example you may open glade file
  as xml in Snaked (``Enter``) or show it in Glade Designer (``<ctrl>Enter``).

* At very bottom there is project combo box, it allows switch between project
  paths being searched. ``<alt>Up`` and ``<alt>Down`` keys change its value.

* ``<ctrl>p`` popups project combo box for easy selecting from large list.

* ``<ctrl>o`` shows standard file choose dialog.


Save positions
--------------

Remembers current file position on editor close and restores it on open.


Search
------

Plugin for text searching. It isn't too much powerful at this moment.

``<ctrl>f`` shows dialog. ``Escape`` hides it. ``<ctrl>j``, ``<ctrl>k`` shows
next/previous match.

I'm still thinking about replace implementation. All variants are too monstrous.
Best way seems ``%s/search/replace/g``. Have any ideas? :ref:`Share it <contacts>`.
