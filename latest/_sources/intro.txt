About Snaked
============

`Snaked`_ (**snak**\ e **ed**\ itor) is light and minimalist editor inspired by
`Scribes`_, mainly targeting python developers, it's
generic enough to please other kind of users too.


Motivation
----------

Why did I start this project? I was looking for a good python editor for a long time, tried
many IDEs but nothing fit my needs: fast, quick project navigation, flexible
code assist tuning, easy to extend.

* `PyDev`_. Almost ideal solution. But very hard to extend.

* `Netbeans`_. It's only a toy. Poor editing capabilities. Very poor auto
  completion.

* `PyCharm`_. Single project edition only. Too bad, I too often edit modules from
  several projects simultaneously.

* Vim + `ropevim`_. May be this is funny, but it is very slow, especially on my
  netbook with syntax highlight and bracket matching enabled. It's also hard to
  extend. However, I love vim, really, it's editing experience is cool and I use
  it for all my non coding tasks.

* Emacs + `ropemacs`_. It is completely new environment to me. Will take too long to learn.

* `WingIDE`_. Very good auto completion. Other features are terribly
  implemented.


Some words about `Scribes`_. This editor impress me. It shows how one have to
design editors (from UI point of view).  Moreover, I started to develop plugins fitting my
needs. For extending I could use my existing PyGtk experience. It's like my dream
come true, but few reasons forced me to start hacking Snaked.

* Scribes internal architecture. Many little classes with spread out behaviour
  responsibility. Message passing is based on GObject signals, that's a pain
  when you try to figure out how some features are implemented.

* Overall code style. Ignoring :pep:`8`. Groundless using of private attributes. Almost
  no white spaces in the code. Scribes sources are hard to read. The gtk
  main loop invocation is pointless. Objects are manually destroyed. There is
  too much boilerplate code and tons of copy/pasting.

* Strange author's opinion about plugins and their dependencies distribution.

After estimating the line count of a light gtksourceview
wrapper of my own, I decided to write Snaked.


Goals
-----

* As little code base as possible. GtkSourceView gives enough features. Editor
  core should only implement `editor` and `project` abstractions, provide
  `plugin system`.
  Preferences dialogs implemented for editor settings, shortcut
  configuration and to choose active plugins from available extensions list.

* Clean and maintainable code and design.

* Tabs! I'm using awesome tiling wm, so Scribes lack of tabs is not a problem
  for me.  But most users complain about it.

* Speed. All development will be made on some Atom Netbook. Scribes is too slow on
  this hardware.

* Memory footprint. Scribes internals are too complicated to trace because of "spaghetti" object
  references and editor leaks like bloody shit. Weakrefs will save the world.

* Flexible plug-in system based on standard python packaging methods.


.. _minimalist-mean:

What does `minimalist` mean?
----------------------------

First of all it is an absence of user interface noise. During file edit you only
need to see text view. Toolbar, menubar, statusbar or project browser are
useless. Hence main Snaked principle -- you see what you need to see.

In the second hand you don't need some feature already provided by another tool. For
example, a project browser (to look at project's structure or to do file operations)
will never be implemented, because File Managers are intended for such tasks.

And third minor claim: there are no widgets designed for mouse-only control.
For example tab close buttons, toolbars and so on.

However, `minimalist` doesn't mean feature poor. I have a bunch of ideas
increasing developer's productivity which are waiting to be implemented. If you
also have suggestions I'll be glad to listen to them.


.. _snaked: http://github.com/baverman/snaked
.. _scribes: http://scribes.sourceforge.net
.. _pydev: http://pydev.org
.. _netbeans: http://netbeans.org
.. _ropevim: http://rope.sourceforge.net/ropevim.html
.. _ropemacs: http://rope.sourceforge.net/ropemacs.html
.. _wingide: http://www.wingware.com/
.. _pycharm: http://www.jetbrains.com/pycharm/
