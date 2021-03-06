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

Once it is installed, you can run the tests to make sure your system is properly _setup, and all required
dependencies are available.

::

   $ python -m unittest -v test.test_ioc.py


Write your first IOC
====================
Your IOC application can be structured at will although we recommend the following directory template

::

   myioc
   ├── bin
   │   ├── runIOC.py    # Command to run IOC Application
   │   └── runOpCtrl    # Command to run Operator Display Application
   ├── opi              # Directory containing Operator Display screens
   └── myioc            # Python package for your IOC Application and all other supporting modules
       ├── __init__.py
       └── ioc.py       # IOC module containing your IOC application


A program is included to create a default IOC project.

::

   $ softdev-startproject myioc

That will create a directory structure similar to the one listed above, except the `runOpCtrl` file which you
will have to create yourself based on your preferred EPICS display manager.


Creating the IOC Model
======================
If you are familar with the Django Framework, the IOC model should feel natural. All IOC models should inherit
from **softioc.models.Model** and declare database records using the record types defined in **softioc.models**.

For example:


.. code-block:: python

   from softdev import models

   class MyIOC(models.Model):
       enum = models.Enum('enum', choices=['ZERO', 'ONE', 'TWO'], default=0, desc='Enum Test')
       toggle = models.Toggle('toggle', zname='ON', oname='OFF', desc='Toggle Test')
       sstring = models.String('sstring', max_length=20, desc='Short String Test')
       lstring = models.String('lstring', max_length=512, desc='Long String Test')
       intval = models.Integer('intval', max_val=1000, min_val=-1000, default=0, desc='Int Test')
       floatval = models.Float(
           'floatval', max_val=1e6, min_val=1e-6, default=0.0,
           prec=5, desc='Float Test'
       )
       floatout = models.Float('floatout', desc='Test Float Output')
       intarray = models.Array('intarray', type=int, length=16, desc='Int Array Test')
       floatarray = models.Array('floatarray', type=float, length=16, desc='Float Array Test')
       calc = models.Calc(
           'calc', calc='A+B',
           inpa='$(device):intval CP NMS',
           inpb='$(device):floatval CP NMS',
           desc='Calc Test'
       )

Once the model is defined, it can then be instanciated within the application. For example:

.. code-block:: python

   ioc = MyIOC('MYIOC-001')

.. autoclass:: softdev.models.Model
   :members:

This will create an IOC database with Process variable fields **MYIOC-001:enum, MYIOC-001:toggle, ...** etc, where
the process variable name is generated based on the model name, and the field name.  Once instanciated, the IOC is ready
to be used and alive on the Channel Access network. However, for more responsive applications, it is recommended to
to create an IOC Application as well.

.. seealso:: `Record Types`_ for detailed documentation about database records.

Creating the IOC Application
============================
The IOC Application manages the IOC database and should provide the logic for the application. This can include
connecting to a device through a serial interface, over the network, handling commands from the model, processing and
generating new values for the database fields, etc. The sky is the limit.

For example, let us create an application which uses the model above and responds to changes to the **MYIOC-001:toggle**
field.

.. code-block:: python

      class MyIOCApp(object):

       def __init__(self, device_name):
           self.ioc = MyIOC(device_name, callbacks=self)

       def do_toggle(self, pv, value, ioc):
           """
           I am called whenever the `toggle` record's value changes
           """
           if value == 1:
               # Command activated, value will return to 0 after some time
               print('Toggle Changed Value', value)
               ioc.enum.put((ioc.enum.get() + 1) % 3, wait=True)  # cycle through values

       def do_enum(self, pv, value, ioc):
           print('New Enum Value', value)

       def shutdown(self):
           # needed for proper IOC shutdown
           self.ioc.shutdown()


This application is initialized with the IOC device name.

Running the IOC Application
===========================
The script **bin/runIOC.py** is responsible for running the IOC Application. An example script is generated by the
**softdev-startproject** command. It can be modified to suit your needs. For example:

.. code-block:: python

   #!/usr/bin/env python
   import os
   import logging
   import sys
   import argparse

   # Twisted boiler-plate code.
   from twisted.internet import gireactor
   gireactor.install()
   from twisted.internet import reactor

   # add the project to the python path and inport it
   sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   from softdev import log
   from myioc import ioc

   # Setup command line arguments
   parser = argparse.ArgumentParser(description='Run IOC Application')
   parser.add_argument('-v', action='store_true', help='Verbose Logging')
   parser.add_argument('--device', type=str, help='Device Name', required=True)


   if __name__== '__main__':
       args = parser.parse_args()
       if args.v:
           log.log_to_console(logging.DEBUG)
       else:
           log.log_to_console(logging.INFO)

       # initialize App
       app = ioc.MyIOCApp(args.device)

       # make sure app is properly shutdown
       reactor.addSystemEventTrigger('before', 'shutdown', app.shutdown)

       # run main-loop
       reactor.run()


This example uses the `Twisted <https://pypi.org/project/Twisted/>`_ framework. It is highly recommended to use it too.

Record Types
============

Records are defined within the **softdev.models** module. The following record types
are currently supported:

.. py:currentmodule:: softdev.models

.. autoclass:: Record
.. autoclass:: Enum
.. autoclass:: BinaryInput
.. autoclass:: BinaryOutput
.. autoclass:: Toggle
.. autoclass:: Integer
.. autoclass:: Float
.. autoclass:: String
.. autoclass:: Array
.. autoclass:: Calc
.. autoclass:: CalcOut


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
