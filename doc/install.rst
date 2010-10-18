.. _install:

Installation
============

Dependencies
------------

* Python 2.6 or 2.7. Python3 support will be with gtk3 and gobject introspection
  framework release.

* PyGtk >= 2.10
  
* pygtksourceview >= 2.10


From PYPI
---------

I'm regularly upload packages of new versions. So you can install Snaked with
``easy_install``::

   sudo easy_install snaked

or `pip`_::

   sudo pip install snaked


Also, with pip you can install Snaked locally::

   pip install snaked --user

In this case executable script will be placed in ``$HOME/.local/bin``


From source
-----------

::

   git clone --depth=1 git://github.com/baverman/snaked.git
   cd snaked
   python setup.py build
   sudo python setup.py install


.. _pip: http://pip.openplans.org/
