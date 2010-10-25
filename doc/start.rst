Getting started
===============

This section explains how to start Snaked, perform basic editing and configure
it.

Running
-------

After :ref:`installation <install>` ``snaked`` script will be created.
You can run it either from terminal or run dialog::

   snaked

:ref:`Quick Open dialog <quick-open>` will be shown after Snaked's start to
allow one open first file.


This command will run snaked with specified file::

   snaked /tmp/first_snaked_file.py


.. image:: /images/first-run.*
   :align: center

.. note::

   Specified file do not need to exist. Snaked will create it after first save.

You can give several filenames to snaked::

   snaked /tmp/first_snaked_file.py /tmp/second_snaked_file.py

And each file will be opened in own tab.

.. image:: /images/second-run.*
   :align: center

One can switch tabs on ``<alt>Left``/``<alt>Right`` keys.


Project navigation
------------------

But specifying file names every time is too annoying, how can one open project
file from Snaked itself? Solution is `Quick Open` dialog. Default shortcut
``<ctrl><alt>r``:

.. image:: /images/quick-open.*

Here it is very common Snaked dialog -- search entry at of the top and list view
below. It is used for preferences finding and python outline navigation also.

Behavior is very simple: you type several characters of subject to find,
"``se``" in my case and dialog shows variants to select. ``Up``/``Down``
navigate between items, ``Enter`` activates selection, ``<alt>s`` focuses search
entry again.

Quick Open provides :ref:`additional functionality <quick-open>`:


Sessions
--------

Snaked provides sessions to store open editors on quit, they allow you omit
files at all. What you have to do to enable sessions?

Run Snaked with ``-s`` (``--session``) option with session name. For example::

   snaked -s test /tmp/first_snaked_file.py

Now, after closing editor by ``<ctrl>q`` key or closing window by wm facilities
``test`` session will be created and you can open it with simple command::

   snaked -s test

Also there is ability to select session at snaked start::

   snaked --select-session


Think about sessions like some sort of workspaces which are separate you tasks.
One session for task or project or whatever.


Preferences
-----------

Preferences dialog is shown on ``<ctrl>p`` key:

.. image:: /images/prefs.*

It is alike Eclipse's quick settings. You need to type what you want to
configure (`font`, `key`, etc.) and select wanted item. 

There are only three core configuration dialogs.

Key configuration
*****************

Here you can see all Snaked shortcuts, and change them:

.. image:: /images/keys.*


Editor settings
***************

Allow one to tune editor theme, font, tabs, margin and so on.

.. image:: /images/editor-prefs.*

Every gtksourceview language can have own settings. Also there is special
language ``default``, it's settings spread over all langs. For example you can
change style theme for ``default`` language and editors for other langs will be
use it automatically.


Plugins
*******

Simple list with available extension. Check to enable, uncheck to disable,
nothing more. If plugin will provide it's own configuration dialog it will
appear in preferences.

.. image:: /images/plugins.*


Default editor shortcuts
------------------------

These key bindings are provided by gtksourceview itself and can't be changed (at
least now).

* ``Tab`` / ``<shift>Tab`` -- (de)indents current line or selection.

* ``<ctrl>Space`` -- pop up completion dialog if any completions providers
  was associated with editor. There is only python provider now.

* ``<ctrl>c`` / ``<ctrl>v`` / ``<ctrl>x`` -- standard copy/paste/cut editor
  shortcuts. Also there are common ``<ctrl>Insert`` / ``<shift>Insert`` / ``<shift>Delete``.

* ``<ctrl>z`` / ``<ctrl>y`` -- undo/redo

* ``<alt>Up`` / ``<alt>Down`` -- moves selection up or down. Very useful feature,
  especially with smart select.
