Snaked
======

Very light and minimalist editor inspired by Scribes. Snaked
intended mostly for python developers but other Scribes users
may find it useful too.

Shortly, Snaked is Scribes with blackjack and bitches.


Goals
-----

- As little code base as possible. GtkSourceView gives enough
  features. Editor core should only implement `project`, `shortcut`,
  `plugin`, `editor title` and `editor problems` abstractions.
  1000 - 3000 cloc's of python code estimated.

- Clean and maintainable code design. Say no for Scribes signal passing hell.

- Tabs! I'm using awesome tiling wm, so Scribes lacking of tabs is not a problem for me.
  But many users complain about it.

- Speed. All development will be maid on Atom Netbook. Scribes is too slow on this hardware.

- Memory footprint. Scribes internals is too complicated to trace all object references
  and editor leaks like bloody shit. Weakrefs will save the world.

- Flexible plugin system based on standard python packaging practices.


Current status
--------------

I use Snaked for all my python development tasks. Following features are implemented.

- Quick open on ``<ctrl><alt>r``.
- Goto python definition on ``F3``.
- Complete words on ``<alt>slash``.
- Pretty title for python modules.
- Python code completion on ``<ctrl>space``
- Smart block selection on ``<alt>w``


Todo
----

Features to implement in nearest time (day or two):

- Storing last edit position for every file.
- Python smart indent.
- Smart select (word -> quotes) with one key. Block selection done.
- Tabs!
- Sessions?
