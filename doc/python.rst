Python plugin
=============

Strictly for the sake of this plugin I started Snaked's development. It requires
`rope <http://rope.sourceforge.net/>`_ for it's work.

Pretty editor title formating
-----------------------------

Package modules are presented like `package.module` or `package` instead
`module.py` or `__init__.py`. Very useful extension to distinguish similar file
names. Must have for every Pytonier.


.. _python-goto-definition:

Goto Definition
---------------

Default ``F3`` shortcut navigates to symbol definition under cursor. It also
handles symbols in quotes and comments. Like::

   def func(param):
      """Some function

      :param param: Some param of some_package.some_module.SomeClass
      """
      pass

To see ``param`` class you need to place cursor on ``SomeClass`` and hit ``F3``.
Or if rope can infer ``param`` type you can place cursor there and hit ``F3``.


.. _python-autocomplete:

Code completion
---------------

Snaked uses gtksourceview2's completion framework. I've only implement python
provider. All UI work are done by gtksourceview.

.. image:: /images/complete.*

``<ctrl>space`` activates popup. Also there is support for showing pydocs in
detailed proposal information.


.. _python-outline:

Outline navigation
------------------

This dialog provides easy jumping into needed module block.

.. image:: /images/outline1.*

.. image:: /images/outline2.*


.. _python-type-hints:

Type hints
----------

This is the most exiting Snaked's part. It allows to provide additional type
information to rope for better type inferring and as consequence better
completion and code navigation.

What hints can be provided:

* Function/method param types.

* Function/method return type.

* Replacing module attribute.

* Adding attributes to class.


Usage
*****

There is special file to configure hints: ``.ropeproject/ropehints.py`` in your
project root. It is ordinary python file which must define function
``init(provider)``, where ``provider`` is default project hint provider with
build-in scope matcher and doc string hint support.

Take note, without configured hints you have doc string hint provider anyway.


Snaked's hint providers
***********************
.. currentmodule:: snaked.plugins.python.ropehints

.. autoclass:: CompositeHintProvider
   :members:

.. autoclass:: ScopeHintProvider
   :members: __init__


.. currentmodule:: snaked.plugins.python.dochints

.. autoclass:: DocStringHintProvider

Snaked's scope matchers
***********************
.. currentmodule:: snaked.plugins.python.ropehints

.. autoclass:: ReScopeMatcher
   :members:

Django hints
************

Look at image:

.. image:: /images/django-hints.*

Cool, isn't it? Simply add django support into your ``.ropeproject/ropehints.py``::

   def init(provider):
       from snaked.plugins.python.djangohints import add_django_support
       add_django_support(provider)

.. note::
   Django hints were developed against django 0.97 (yeah, I maintain such old
   project) codebase and not tested on current versions. Get me know if you
   will have any issues.

PyGtk hints
***********

Image again:

.. image:: /images/pygtk-hints.*

Who is there? ``BuilderAwere`` is a simple wrapper which delegates missing
attributes to GtkBuilder. ``Window`` is ``BuilderAware`` class constructed from
glade file. ``vbox1`` is a GtkVBox defined in glade file and PyGtk hint provider
resolves class attributes from it.

Besides that, goto definition (``F3``) opens glade file and place cursor at ``vbox1``
declaration.

And more, if there are any signal handlers in glade file they parameters also will
be resolved.

You only need to add pygtk support and assign glade file to class via ``ropehints.py``::

   def init(provider):
       from snaked.plugins.python.pygtkhints import add_gtk_support

       pygtk = add_gtk_support(provider)
       pygtk.add_class('gui.Window', 'main.glade')
