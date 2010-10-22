Snaked
======

Very light and minimalist editor inspired by Scribes. Snaked
intended mostly for python developers but other Scribes users
may find it useful too.

Shortly, Snaked is Scribes with blackjack & hookers.

Documentation
-------------

May be found at http://packages.python.org/snaked/index.html


Goals
-----

- As little code base as possible. GtkSourceView gives enough
  features. Editor core should only implement `project`, `shortcut`,
  `plugin`, `editor title` and `editor problems` abstractions.
  1000 - 3000 cloc's of python code estimated.

- Clean and maintainable code design. Say no for Scribes signal passing hell.

- Tabs! I'm using awesome tiling wm, so Scribes lacking of tabs is not a problem for me.
  But many users complain about it.

- Speed. All development will be made on Atom Netbook. Scribes is too slow on this hardware.

- Memory footprint. Scribes internals is too complicated to trace all object references
  and editor leaks like bloody shit. Weakrefs will save the world.

- Flexible plugin system based on standard python packaging practices.


Current status
--------------

I use Snaked for all my python development tasks. Following features are implemented:

- Quick open on ``<ctrl><alt>r``.
- Goto python definition on ``F3``.
- Complete words on ``<alt>slash``.
- Pretty title for python modules.
- Python code completion on ``<ctrl>space``.
- Storing last edit position for every file.
- Python smart indent.
- Saving quick open project history and switch between them on ``<alt>Up``/``<alt>Down``.
- Tabs. Switching on ``<alt>Left/<alt>Right``.
- Python outline navigator on ``<ctrl>o``.
- Feedback messages api. For example syntax errors on python autocomplete and so on.
- Hash comment plugin for commenting python, ruby, etc... code. Activated on ``<ctrl>slash``.
- Improved smart block selection algorithm.
- pyflakes integration (very basic now)
- Goto line on ``<ctrl>l``
- Goto dir on ``<ctrl><alt>l``
- Session to store opened editors on application quit.
- Search on ``<ctrl>f``
- Smart anything selection on ``<alt>w``. Just try it!
- Plugin manager to allow one enable/disable installed plugins
- Shortcut manager
- Preferences dialog
- Editor preferences. Font, tabs and so on. Activated by ``<ctrl>p``
- Python type hints defining. One can override function parameters, return and
  module attributes types.

Current progress may be seen in `@a_bobrov <http://twitter.com/a_bobrov>`_.

