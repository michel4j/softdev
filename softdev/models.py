import collections
import multiprocessing
import os
import shutil
import subprocess
import time

from . import epics, log

ENUM_KEYS = [
    'ZR', 'ON', 'TW', 'TH', 'FR', 'FV', 'SX', 'SV',
    'EI', 'NI', 'TE', 'EL', 'TV', 'TT', 'FT', 'FF'
]

logger = log.get_module_logger(__name__)


class RecordType(type):
    """Record MetaClass"""

    def __new__(cls, name, bases, dct):
        # append required kwargs
        dct['required'] = getattr(bases[0], 'required', []) + dct.get('required', [])

        # update fields
        fields = {}
        fields.update(getattr(bases[0], 'fields', {}))
        fields.update(dct.get('fields'))
        dct['fields'] = fields

        return super(RecordType, cls).__new__(cls, name, bases, dct)


class Record(object):
    __metaclass__ = RecordType
    required = ['name', 'desc']
    record = 'ai'
    fields = {
        'DTYP': '{channel}',
        'DESC': '{desc}',
    }

    def __init__(self, name, desc=None, raw=False, **kwargs):
        """
        Base class for all record types
        :param name: Record name (str)
        :param desc: Description (str)
        :param raw: (bool) whether to use raw soft channel or soft channel
        :param kwargs: additional keyword arguments
        """
        kwargs.update(name=name, desc=desc)
        kw = {k: v for k, v in kwargs.items() if v is not None}
        self.options = {}
        self.options.update(kw)
        self.options['record'] = self.record
        self.options['channel'] = 'Soft Channel' if not raw else 'Raw Soft Channel'
        self.instance_fields = {}
        self.instance_fields.update(self.fields)
        missing_args = set(self.required) - set(self.options.keys())
        assert not missing_args, '{}: Missing required kwargs: "{}"'.format(self.__class__.__name__,
                                                                            ', '.join(missing_args))

    def __str__(self):
        template = '\n'.join(
            ['record({record}, "$(device):{name}") {{'] +
            ['  field({}, "{}")'.format(k, v) for k, v in self.instance_fields.items()] +
            ['}}', '']
        )
        return template.format(**self.options)

    def add_field(self, key, value):
        """
        Add a database record field
        :param key: field name
        :param value: field value
        :return:
        """
        self.instance_fields[key] = value

    def del_field(self, key):
        """
        Delete a database record field
        :param key: field name
        :return:
        """
        if key in self.instance_fields:
            del self.instance_fields[key]


class Enum(Record):
    required = ['choices']
    record = 'mbbo'
    fields = {
        'VAL': '{default}'
    }

    def __init__(self, name, choices=None, default=0, **kwargs):
        """
        Enum record type
        :param name: Record name (str)
        :param choices: list/tuple of strings corresponding to the choice names, values will be 0-index integers
        :param default: default value of the record, 0 by default
        :param kwargs: Extra keyword arguments
        """
        kwargs.update(choices=choices, default=default)
        super(Enum, self).__init__(name, **kwargs)
        if isinstance(self.options['choices'], collections.Iterable):
            for i, (key, name) in enumerate(zip(ENUM_KEYS, self.options['choices'])):
                self.add_field('{}VL'.format(key), "{}".format(i))
                self.add_field('{}ST'.format(key), name)


class Toggle(Record):
    record = 'bo'
    fields = {
        'ZNAM': '{zname}',
        'ONAM': '{oname}',
        'HIGH': '{high:0.2g}'
    }

    def __init__(self, name, high=0.25, zname=None, oname=None, **kwargs):
        """
        Toggle field corresponding to a binary out record.

        :param name: Record name (str)
        :param high: Duration to keep high before returning to zero
        :param zname: string value when zero
        :param oname: string value when high
        :param kwargs: Extra keyword arguments
        """
        zname = kwargs['desc'] if not zname else zname
        oname = kwargs['desc'] if not oname else oname
        kwargs.update(high=high, zname=zname, oname=oname)
        super(Toggle, self).__init__(name, **kwargs)


class String(Record):
    required = ['max_length']
    record = 'stringout'
    fields = {
        'VAL': '{default}'
    }

    def __init__(self, name, max_length=20, default='', **kwargs):
        """
        String record. Uses standard string record, or character array depending on length
        :param name: Record name (str)
        :param max_length: maximum number of characters expected
        :param default:  default value, empty string by default
        :param kwargs: Extra keyword arguments
        """
        kwargs.update(max_length=max_length, default=default)
        super(String, self).__init__(name, **kwargs)
        if self.options['max_length'] > 20:
            self.options['record'] = 'waveform'
            self.add_field('NELM', self.options['max_length'])
            self.add_field('FTVL', 'CHAR')
            self.del_field('VAL')


class Integer(Record):
    record = 'longout'
    required = ['units']
    fields = {
        'HOPR': '{max_val}',
        'LOPR': '{min_val}',
        'VAL': '{default}',
        'EGU': '{units}',
    }

    def __init__(self, name, max_val=1000000, min_val=-1000000, default=0, units='', **kwargs):
        """
        Integer Record.

        :param name: Record Name.
        :param max_val: Maximum value permitted (int), default (1e6)
        :param min_val: Minimum value permitted (int), default (-1e6)
        :param default: default value, default (0)
        :param units:  engineering units (str), default empty string
        :param kwargs: Extra keyword arguments
        """
        kwargs.update(max_val=max_val, min_val=min_val, default=default, units=units)
        super(Integer, self).__init__(name, **kwargs)


class Float(Record):
    record = 'ao'
    required = ['units']
    fields = {
        'DRVL': '{max_val:0.4e}',
        'DRVH': '{min_val:0.4e}',
        'LOPR': '{max_val:0.4e}',
        'HOPR': '{min_val:0.4e}',
        'PREC': '{prec}',
        'EGU': '{units}',
        'VAL': '{default}'
    }

    def __init__(self, name, max_val=1e10, min_val=-1e10, default=0.0, prec=4, units='', raw=True, **kwargs):
        """
        Float Record.

        :param name: Record Name.
        :param max_val: Maximum value permitted (float), default (1e6)
        :param min_val: Minimum value permitted (float), default (-1e6)
        :param default: default value, default (0.0)
        :param prec: number of decimal places, default (4)
        :param units:  engineering units (str), default empty string
        :param kwargs: Extra keyword arguments
        """
        kwargs.update(max_val=max_val, min_val=min_val, default=default, prec=prec, raw=raw, units=units)
        super(Float, self).__init__(name, **kwargs)


class Calc(Record):
    record = 'calc'
    required = ['calc']
    defaults = {
        'scan': 0,
        'prec': 4,
    }
    fields = {
        'CALC': '{calc}',
        'SCAN': '{scan}',
        'PREC': '{prec}',
    }

    def __init__(self, name, scan=0, prec=4, **kwargs):
        """
        Calc Record

        :param name: Record name
        :param scan: scan parameter, default (0 ie passive)
        :param prec: number of decimal places, default (4)
        :param kwargs: Extra keyword arguments
        """
        kwargs.update(scan=scan, prec=prec)
        super(Calc, self).__init__(name, **kwargs)
        for c in 'ABCDEFGHIJKL':
            key = 'INP{}'.format(c)
            if key.lower() in self.options:
                self.add_field(key, self.options[key.lower()])


class CalcOut(Calc):
    record = 'calcout'
    fields = {
        'OOPT': 0,
        'DOPT': 0,
        'OUT': '{out}'
    }

    def __init__(self, name, out='', **kwargs):
        """
        CalcOutput Record

        :param name: Record name
        :param out: Output record
        :param kwargs: Extra keyword arguments, supports Calc kwargs also.
        """
        kwargs.update(out=out)
        super(CalcOut, self).__init__(name, **kwargs)


class Array(Record):
    record = 'waveform'
    required = ['type', 'length']
    fields = {
        'NELM': '{length}',
        'FTVL': '{type}',
    }

    def __init__(self, name, type=int, length=None, **kwargs):
        """
        Array Record.

        :param name: Record Name
        :param type: Element type (str or python type), supported types are ['STRING', 'SHORT', 'FLOAT', int, str, float]
        :param length: Number of elements in the array
        :param kwargs: Extra kwargs
        """
        kwargs.update(type=type, length=length)
        super(Array, self).__init__(name, **kwargs)
        element_type = self.options['type']
        self.options['type'] = {
            str: 'STRING',
            int: 'LONG',
            float: 'FLOAT',
        }.get(element_type, element_type)


CMD_TEMPLATE = """
## Load record instances
dbLoadRecords {db_name}.db, device={device_name}
iocInit()
dbl
"""


class ModelType(type):
    def __new__(cls, name, bases, dct):
        fields = {}
        for k, v in dct.items():
            if isinstance(v, Record):
                fields[k] = v
                del dct[k]
        dct['_fields'] = fields
        return super(ModelType, cls).__new__(cls, name, bases, dct)


class Model(object):
    """
    IOC Database Model.

    SubClasses should define record attributes at the top-level of the class declaration for example:

        class MyIOC(Mode):
            pv1 = Integer('pv1', desc='Test Integer PV')
            pv1 = Integer('pv1', desc='Test Integer PV')
    """
    __metaclass__ = ModelType

    def __init__(self, device_name, callbacks=None, command='softIoc'):
        """
        IOC Database Model Instance
        :param device_name:  Root Name of device, process variable records will be named '<device_name>:<record_name>'
        :param callbacks: Object which provides callback methods for handling events and commands, if not provided,
            it is assumed that all callbacks are defined within the model itself. The expected callback methods
            should follow the signature:

                def do_<record_name>(self, pv, value, ioc)

            which accepts the active record (pv), the changed value (value) and the ioc instance (ioc).

            If the Model is also the callbacks provider, self, and ioc are identical, otherwise ioc is a reference
            to the database model on which the record resides.
        :param command: The softIoc command to execute. By default this is 'softIoc' from EPICS base. For example you
            could chose to use xxx from synApps.
        """
        self.device_name = device_name
        self.callbacks = callbacks or self
        self.ioc_process = None
        self.command = command
        self.ready = False
        self.db_cache_dir = os.path.join(os.path.join(os.getcwd(), '__dbcache__'))
        self.start_ioc()
        self.setup()

    def start_ioc(self):
        """
        Generate the database and start the IOC application in a separate process
        :return:
        """
        if not os.path.exists(self.db_cache_dir):
            os.mkdir(self.db_cache_dir)
        db_name = self.__class__.__name__
        with open(os.path.join(self.db_cache_dir, '{}.db'.format(db_name)), 'w') as db_file:
            for k, v in self._fields.items():
                db_file.write(str(v))

        with open(os.path.join(self.db_cache_dir, '{}.cmd'.format(db_name)), 'w') as cmd_file:
            cmd_file.write(CMD_TEMPLATE.format(device_name=self.device_name, db_name=db_name))
        os.chdir(self.db_cache_dir)
        self.ioc_process = multiprocessing.Process(
            target=subprocess.check_call,
            args=([self.command, '{}.cmd'.format(db_name)],),
            kwargs={'stdin': subprocess.PIPE}
        )
        self.ioc_process.daemon = True
        self.ioc_process.start()

    def stop_ioc(self):
        """
        Shutdown the ioc application
        :return:
        """
        self.ioc_process.terminate()
        shutil.rmtree(self.db_cache_dir)

    def setup(self):
        """
        Set up the ioc records an connect all callbacks
        :return:
        """
        pending = set()
        for k, f in self._fields.items():
            pv_name = '{}:{}'.format(self.device_name, f.options['name'])
            pv = epics.PV(pv_name)
            pending.add(pv)
            setattr(self, k, pv)
            callback = 'do_{}'.format(k).lower()
            if hasattr(self.callbacks, callback):
                pv.connect('changed', getattr(self.callbacks, callback), self)

        # wait 10 seconds for all PVs to connect
        timeout = 5
        while pending and timeout > 0:
            time.sleep(0.05)
            timeout -= 0.05
            pending = {pv for pv in pending if not pv.is_active()}

        print('')
