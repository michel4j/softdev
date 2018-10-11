.. SoftDev documentation master file, created by
   sphinx-quickstart on Wed Oct 10 16:34:06 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

SoftDev
=======

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Overview
========
SoftDev is a package which enables python based EPICS IOC Soft Device support all within python. It
allows you to define the IOC database model in a manner similar to Django Database models, and to use
the model to develop dynamic, IOC servers.

It includes a python ctypes based EPICS Channel Access interface based on `PyGObject`. For use the
full capabilities, it is is highly recommended to use a GObject compatible main loop, such as the
one provided by `PyGObject` or even better, the GObject compatible `Twisted` reactor.

This library has been used to support very complex network IOC devices with non-trivial communication
protocols. It works!

Getting Started
===============
Before you can use SoftDev, you'll need to install it. It is a pure python module, although it requires
`PyGObject <https://pypi.org/project/PyGObject/>`_ and `Numpy <https://pypi.org/project/numpy/>`_ to be available.
`Twisted <https://pypi.org/project/Twisted/>`_  is also highly recommended.

SoftDev Also requires a fully functional `EPICS Base <https://epics.anl.gov/base/index.php>`_ installation. If you haven't so yet,
please build and install EPICS Base. It has been tested with EPICS Base versions 3.14 to 3.16.


.. note::
    SoftDev does not use `pyepics <https://pypi.org/project/pyepics/>`_. It includes a python module for accessing EPICS Channel Access. It is not
    trivial to replace the built-in EPICS support with `pyepics`. It is uncertain how well both libraries will
    can interact within the same application. We recommend not using `pyepics` within your SoftDev IOC application.

Once it is installed, you can run the tests to make sure your system is properly setup, and all required
dependencies are available.

::

   $ python -m unittest -v tests.ioc_tests


Write your first IOC
====================
Your IOC application can be structured at will although we recommend the following directory template

::

   myioc
   ├── bin
   │   ├── runIOC.py    # Command to run IOC Application
   │   └── runOpCtrl    # Command to run Operator Display Application
   ├── op               # Directory containing Operator Display screens
   └── myioc            # Python package for your IOC Application and all other supporting modules
       └── ioc.py       # IOC module containing your IOC application

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
