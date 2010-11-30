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

If you often pull changes from master brunch I recommend you following recipe:

* First install snaked in develop mode (remove any snaked dirs in site-packages
  before that)::

     sudo python setup.py develop

* Then, if you want use latest snaked from master branch simply do::

     cd cloned/snaked/dir
     git pull


.. _pip: http://pip.openplans.org/
