Getting started
===============

This section explains how to start Snaked, perform basic editing tasks and configure
it.

Running
-------

After :ref:`installation <install>` ``snaked`` script will be created.
You can run it either from terminal or run dialog::

   snaked

:ref:`Quick Open dialog <quick-open>` will be shown after Snaked's start to
allow one open first file.


This command will start snaked with a specified file opened::

   snaked /tmp/first_snaked_file.py


.. image:: /images/first-run.*
   :align: center

.. note::

   Specified file do not need to exist. Snaked will create it automatically on save operation.

You can provide several filenames to snaked::

   snaked /tmp/first_snaked_file.py /tmp/second_snaked_file.py

And each file will be opened in own tab.

.. image:: /images/second-run.*
   :align: center

One can switch tabs on ``<alt>Left``/``<alt>Right`` keys.

.. _quick-open:

Project navigation
------------------

Since specifying file names every time is too annoying, how one can open project
file from Snaked itself?
The solution is `Quick Open` dialog. Default shortcut
``<ctrl><alt>r``:

.. image:: /images/quick-open.*

Here is a very common Snaked dialog -- search entry at of the top and list view
below. It is also used for preferences finding and python outline navigation.

Behavior is very simple: you type several characters contained in the name you search,
"``se``" in my case and dialog shows variants to select. ``Up``/``Down``
navigate between items, ``Enter`` activates selection, ``<alt>s`` focuses search
entry again.

.. note::
   If there is only one item in the list you can press ``Enter`` without
   setting the focus on the list view.

`Quick Open` searches files only in current project
following these matching rules:

* filename starts with the search term.

* filename contains the search term

* file path contains the search term

* fuzzy match. if search term contains slashes it matches similar file paths. For
  example ``pl/py`` will match ``plugin/python/__init__.py`` or
  ``plugin/name/python.py``

If search entry is empty, `browser mode` is activated. With it you can investigate
project structure in a more common way: ``Enter`` opens directory content and
``Backspace`` returns to upper level.

Shortcuts
*********

* ``<ctrl>Enter`` opens selected item with default system editor. This important
  feature is missing in many other editors. For example you may open glade file
  as xml in Snaked (``Enter``) or show it in Glade Designer (``<ctrl>Enter``).

* At very bottom there is the project choice widget, it allows switching between project
  paths being searched. ``<alt>Up`` and ``<alt>Down`` keys change its value.

* ``<ctrl>p`` popups project combo box for easy selecting from large list.

* ``<ctrl>o`` shows standard file opener dialog.

* ``<ctrl>Delete`` deletes current project from list.


Creating new file
-----------------

Standard GTK open dialog is too frustrating and hard to use from keyboard, so
I implemented the file create panel.

.. image:: /images/create-new-file.*

It provides folder auto-completion as you type. With ``Tab`` key you can cycle
through proposals. ``Esc`` hides dialog, ``Enter`` opens an editor page associated to that file name.


Sessions
--------

Snaked provides sessions to store open editors state on quit, this allow you forget about
files at all. The following steps are required to enable sessions:

Run Snaked with ``-s`` (or ``--session``) option giving a session name. For example::

   snaked -s test /tmp/first_snaked_file.py

Now, after closing editor by ``<ctrl>q`` key or closing window by wm facilities
``test`` session will be created. Thus you can open it with that simple command::

   snaked -s test

You can also select a session on snaked startup::

   snaked --select-session

Think about sessions as some sort of separate workspaces to group your files.
One session for task or project or whatever, use it freely.


Preferences
-----------

Preferences dialog is made available on ``<ctrl>p`` key press:

.. image:: /images/prefs.*

It is like Eclipse's quick settings. You need to type what you want to
configure it (`font`, `key`, etc.) and select wanted item.

There are only three core configuration dialogs.

Key configuration
*****************

Here you can see all Snaked shortcuts, and change them:

.. image:: /images/keys.*


Editor settings
***************

Allow one to tune editor theme, font, tabs, margin and so on.

.. image:: /images/editor-prefs.*

Every gtksourceview language can have its own settings. Also there is a special
language: ``default``, its settings are spread over all langs. For example you can
change style theme for ``default`` language and all editors will
inherit this setting by default.


Plugins
*******

Simple list with available extensions. Check to enable, uncheck to disable,
nothing more. If a plugin provide it's own configuration dialog it will
appear in preferences.

.. image:: /images/plugins.*


Default editor shortcuts
------------------------

These key bindings are provided by gtksourceview itself and can't be changed (at
least now).

* ``Tab`` / ``<shift>Tab`` -- (de)indents current line or selection.

* ``<ctrl>Space`` -- pop up completion dialog if any completions providers
  is associated with editor. Currently the only available provider works for python.

* ``<ctrl>c`` / ``<ctrl>v`` / ``<ctrl>x`` -- standard copy/paste/cut editor
  shortcuts. Also there are common ``<ctrl>Insert`` / ``<shift>Insert`` /
  ``<shift>Delete``.

* ``<ctrl>z`` / ``<ctrl>y`` -- undo/redo

* ``<alt>Up`` / ``<alt>Down`` -- moves selection content up or down. Very useful
  feature,   especially with smart select.


Spot navigation
---------------

Snaked tries to remember important editing places and allows one to
navigate between such spots.

Behavior is not fine tuned yet, but spot navigation satisfy my bookmarking requirements.

How does it work?
*****************

If you move cursor to big distance (PageUp/Down, buffer start/end, switch tab,
goto line, goto definition or moving to spot) a spot is placed. You can also place
some spot manually by pressing ``<alt>T``. Spots are organized in a fixed length stack.

Shortcuts
*********

* ``<alt>Q`` moves to last spot and put current cursor position at top of spot stack.
  Thereby double ``<alt>Q`` brings you back to same position.

* ``<ctrl><alt>Left/Right`` moves to previous/next spot in stack.

* ``<alt>T`` adds a spot with current cursor position on top of stack.

