Snaked user manual
====================

`Snaked`_ (**snak**\ e **ed**\ itor) is light and :ref:`minimalist
<minimalist-mean>` editor inspired by `Scribes`_, indented mostly for python
developers, but other users may find it useful too.

Features:

* Light UI. There are no menu, tool bar, status bar or project browser at all. Only editor view
  itself.

* `gtksourceview2`_ based.

* Keyboard oriented control.

* :ref:`Tabbed <tabbed-interface>` and :ref:`windowed <windowed-interface>`
  (separate window for each editor) interfaces.

* Auto projects. In most cases you do not need such boring operation like
  :menuselection:`File --> New project`. Just start edit your file.

* Project navigation via Quick Open dialog.

* Sessions to store last opened editors.

* Restoring last edit position.

* Python auto complete and navigation via rope.

* Basic python code lint via pyflakes.

* Smart everything selection.

* Common word completer.


.. image:: /images/snaked.*
   :scale: 50%
   :align: center


.. note::

   Just a brief remark: I'm not a native English speaker so you may feel some
   confusion reading this manual.  Please, share your discomfiture with me. I'll
   be very grateful for that.


Content
-------

.. toctree::
   :maxdepth: 2

   intro
   install
   start

.. _snaked: http://github.com/baverman/snaked
.. _scribes: http://scribes.sourceforge.net
.. _gtksourceview2: http://projects.gnome.org/gtksourceview/
