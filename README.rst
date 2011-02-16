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
