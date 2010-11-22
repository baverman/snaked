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
.. module:: snaked.plugins.python.ropehints

.. autoclass:: CompositeHintProvider
   :members:

.. autoclass:: ScopeHintProvider
   :members: __init__


Snaked's scope matchers
***********************
.. autoclass:: ReScopeMatcher
   :members:
