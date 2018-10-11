SoftDev
=======

SoftDev is a package which enables python based EPICS IOC Soft Device support all within python. It
allows you to define the IOC database model in a manner similar to Django Database models, and to use
the model to develop dynamic, IOC servers.

It includes a python ctypes based EPICS Channel Access interface based on `PyGObject`. For use the
full capabilities, it is is highly recommended to use a GObject compatible main loop, such as the
one provided by `PyGObject` or even better, the GObject compatible `Twisted` reactor.

Example:
========

The content of the example **ioc.py** file looks like

``` python

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
```

The **runIOC.py** file looks like the following:


``` python

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

   # Setup single argument for verbose logging
   parser = argparse.ArgumentParser(description='Run IOC Application')
   parser.add_argument('-v', action='store_true', help='Verbose Logging')
   args = parser.parse_args()

   if __name__== '__main__':
       if args.v:
           log.log_to_console(logging.DEBUG)
       else:
           log.log_to_console(logging.INFO)

       # initialize App
       app = ioc.MyIOCApp('APP0000-01')

       # make sure app is properly shutdown
       reactor.addSystemEventTrigger('before', 'shutdown', app.shutdown)

       # run main-loop
       reactor.run()
```

See the more detailed documentation on how to use it.