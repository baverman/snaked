Python plugin
=============

This plugin requires `rope <http://rope.sourceforge.net/>`_ for it's work.

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
Or if rope can infer ``param`` type you can place cursor there and hit
``F3``.


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
information to rope for better type inferring and as consequence better completion
and code navigation.

What hints can be provided:

* Function/method param types.

* Function/method return type.

* Replacing module attribute.


Usage
*****

There is special file for describing hints: ``.ropeproject/hints`` in the your
project root. With following format::

   scope_regex name_regex substitute

For example::

   .* editor$ snaked.core.editor.Editor()  # All function params with 'editor'
                                           # name will be of type
                                           # snaked.core.editor.Editor

   flask$ request$ flask.wrappers.Request()   # flask.request will be of Request
                                              # type, so you can autocomplete
                                              # it's content.

   werkzeug$ Request$ werkzeug.wrappers.Request  # allows rope to see
                                                 # werkzeug.Request

   flask$ g$ app.Context() # flask global context now resolves into your
                           # application class.


There is also short video: http://github.com/downloads/baverman/snaked/hints.mkv
