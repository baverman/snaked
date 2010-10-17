About Snaked
============

`Snaked`_ (**snak**\ e **ed**\ itor) is light and minimalist editor inspired by
`Scribes`_, indented mostly for python developers, but other users may find it
useful too.


Motivation
----------

Why I start this project? I was need a good python editor for a long time, tried
many IDEs but nothing fits my requests: fast, quick project navigation, flexible
code assist tuning, easy to extend.

* `PyDev`_. Almost ideal solution. But very hard to extend.

* `Netbeans`_. It's only a toy. Poor editing capabilities. Very poor auto
  completion.

* `PyCharm`_. Only one project for instance. I too often edit modules from
  several projects simultaneously.

* Vim + `ropevim`_. May be this is funny, but it is very slow, especially on my
  netbook with syntax highlight and bracket matching enabled. Also hard to
  extend. However, I love vim, really, it's editing experience is cool and I use
  it for all my non coding tasks.

* Emacs + `ropemacs`_. It is new environment completely. Too much time to learn.

* `WingIDE`_. Auto complete is very good. Other features are terribly
  implemented.


Some words about `Scribes`_. This editor impress me. It shows how one have to
design editors (from UI point).  Moreover, I started to develop plugins for my
needs. For extending I could use my existing PyGtk experience.  It seemed dream
come true, but few reasons force me to start hack Snaked.

* Scribes internal architecture. Many little classes with spread out behavior
  responsibility.  Message passing based on GObject signals leads to very long
  path to investigate how some features are implemented.

* Overall code style. Ignoring PEP8. Groundless using of private attributes. A
  little whitespace in code. Scribes sources are hard to read. Pointless gtk
  main loop invocation. Manual object destruction. Too much boilerplate code,
  tons of copypasting.

* Strange author's opinion about plugins and it's dependencies distribution.

And after some thoughts about estimated lines count in own light gtksourceview
wrapper, I decide to write Snaked.


Goals
-----

* As little code base as possible. GtkSourceView gives enough features. Editor
  core should only implement `editor` and `project` abstractions, provide
  `plugin system` and preferences dialogs for editor settings, shortcut
  configuration and for choosing active plugins from available extensions.

* Clean and maintainable code design.

* Tabs! I'm using awesome tiling wm, so Scribes lacking of tabs is not a problem
  for me.  But many users complain about it.

* Speed. All development will be maid on Atom Netbook. Scribes is too slow on
  this hardware.

* Memory footprint. Scribes internals is too complicated to trace all object
  references and editor leaks like bloody shit. Weakrefs will save the world.

* Flexible plugin system based on standard python packaging practices.


.. _minimalist-mean:

What does `minimalist` mean?
----------------------------

First of all it is an absence of user interface noise. During file edit you only
need to see text view. Toolbar, menubar, statusbar or project browser are
useless. Hence main Snaked principle -- you see what you need to see.

In the second you do not need a feature which provided by other tool. For
example project browser (to look at project structure or to do file operations)
will never be implemented, because File Managers are intended for such tasks.

And third minor claim: there are no any widgets designed for controlling with
mouse. For example tab close buttons, toolbars and so on.

However, `minimalist` doesn't mean feature poor. I have a bunch of ideas
increasing developer productivity which are waiting to be implemented. If you
also have suggestions I'll listen them with pleasure.


.. _snaked: http://github.com/baverman/snaked
.. _scribes: http://scribes.sourceforge.net
.. _pydev: http://pydev.org
.. _netbeans: http://netbeans.org
.. _ropevim: http://rope.sourceforge.net/ropevim.html
.. _ropemacs: http://rope.sourceforge.net/ropemacs.html
.. _wingide: http://www.wingware.com/
.. _pycharm: http://www.jetbrains.com/pycharm/
