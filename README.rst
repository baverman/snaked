Snaked v0.5 status
==================

Here is some brief highlights for v0.5 development progress.

Changes from v0.4 (implemented already)
---------------------------------------

* Snaked was refactored with `uxie <https://github.com/baverman/uxie>`_.
  It means some important features:

  * All user interaction is divided into contexts (there is only one context in
    v0.4 -- editor) which defines current set of allowed actions and its
    shortcuts.

  * Possible actions can be discovered with a menu. There is no need to
    remember all keys anymore.

  * Flexible shortcut mapping: many keys to one action, one key to multiple
    actions, keybindings for popup menus and for dynamic actions (for example
    one can assign shortcut to external tool!).

  * Shortcut conflict resolution.

  * Feedback messages stack.

* Multiple windows (each with own editor set).

* Multiple editor views for one buffer (yes, editor tab can be detached
  or moved between windows).

* Search within multiple projects in quick open.

* Editor contexts can be nested, defined globally, for session and for project.

* Changed external tools config format, now it is a plain python file with a
  simple eDSL. External tools also can be configured globally and for session.

* Python plugin:

  * Dropped rope support in favor of
    `supplement <https://github.com/baverman/supplement>`_.

  * Py3 support.

  * Py3 support in test runner.

  * Python interpreter selector.

What should be done before v0.5 release
---------------------------------------

* Snippets preferences.

* Nested snippets configs.

* Dynamic external tool contexts (via shell scripts and python functions).

* Ability to spawn external tools on editor events (for example on-save).

* Encoding editor context.

* Encoding selector when chardet fails.

* use_tabs context


How to install and try v0.5dev?
-------------------------------

Install requirements::

   pip install -e git://github.com/baverman/uxie#egg=uxie
   pip install -e git://github.com/baverman/supplement#egg=supplement
   pip-3.2 install -e git://github.com/baverman/supplement@py3#egg=supplement

Last command is needed only for py3 support.

Then::

   pip install -e git://github.com/baverman/snaked#egg=snaked

You need to know only two keys:

* F1 to popup a root menu.
* F2 to edit shortcuts for selected menu item (and remember, you can assign
  key to **ANY** menu item).

I'll appreciate your help in dev version testing before release.

Contacts:

* GH, as usual.
* http://groups.google.com/group/snaked if you have no GH account.
* JID: baverman at jabber dot ru for urgent help.


Snaked
======

Very light and minimalist editor inspired by Scribes. Snaked intended mostly for
python developers but other Scribes users may find it useful too.

Shortly, Snaked is Scribes with blackjack & hookers.


Documentation
-------------

May be found at http://packages.python.org/snaked/index.html
Current docs are a some sort of outdated and match 0.4.6 version.
Work in progress.

Features
--------

* Light UI. There are no menu, tool bar, status bar or project browser at all.
  Only editor view  itself.

* `gtksourceview2 <http://projects.gnome.org/gtksourceview/>`_ based.

* Keyboard oriented control.

* Auto projects. In most cases you do not need such boring operation like
  ``File`` → ``New project``. Just start edit your file.

* Project navigation via Quick Open dialog.

* Sessions to store last opened editors.

* Restoring last edit position.

* Python auto complete and navigation via rope with very flexible type hinting
  framework. PyGtk, Django support.

* Basic python code lint via pyflakes.

* Snippets.

* Unittests (with `py.test <http://pytest.org/>`_ as backend, so there is
  support for usual UnitTest   cases, nose cases and ``py.test`` itself).

* Spell check.


Current status
--------------

Current progress may be seen in `@a_bobrov <http://twitter.com/a_bobrov>`_. Also
there is `blog <http://bobrochel.blogspot.com/search/label/snaked>`_ with
release announces.


ToDo
----

* Variables completion in Mako, Jinja, Django templates.
* REPL
