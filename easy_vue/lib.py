# -*- coding: utf-8 -*-
# @Author  : Alex V Zobov (alex_ins@mail.ru)
# @Link    : 
# @Version : $Id$

from __future__ import unicode_literals

"""
  Набор полезных утилит общего назначения
"""


import numbers
from decimal import Decimal
import time
from datetime import datetime, timedelta
import json

from collections import OrderedDict, Mapping, MutableMapping, Iterable

import dateutil.parser
from dateutil.tz import tzlocal

quartal = lambda x: ((x-1) // 3)+1


class EMessageError(Exception):
    """
      Базовый класс для исключений, имеющих тип, текст в ACII и 
        текст в Unicode, и умеющих выводить этот текст.
        При str или repr используется ename, 
        а при print или unicode - uname.
        К тексту, определенному в классе дописывается текст, переданный при
          генерации экземпляра исключения.

      Атрибуты:
        ename - ASCII текст названия исключения.
        uname - Unicode текст названия исключения
        Определяются, как правило, на уровне класса.
    """
  
    ename = b"Base message error"
    uname = u"Неуточненная ошибка с текстом."

    def __init__(self, mes=""):
        """
        """
        self.s_mes = mes

    def __str__(self):
        return b" ".join((self.ename, self.s_mes))

    def __unicode__(self):
        return u" ".join((self.uname, self.s_mes))


def NZ(val, replace=0):
    """
      Если val is None, возвращает replace
    """
    return replace if val is None else val


def local_str(arg):
    """
      Преобразует arg в unicode, а затем в строку с кодировкой для вывода на текущем терминале
    """
    import sys
    e = sys.stdout.encoding
    if not e:
        e='cp1251'
    return unicode(arg).encode(e, 'ignore')


def strip(val):
    """
      Если val - текстовая строка, убирает пробелы с начала и конца,
      иначе возвращает как есть.
    """
    if hasattr(val, 'strip'):
        return val.strip(' ')
    else:
        return val


def datetime2ts(dt):
    """
      Converts datetime to Unux timestamp
    """
    if dt is None:
        return None
        
    return time.mktime(dt.timetuple())


class ZMoment(object):
    """
      Сохранение даты/времени в/из JSON и в/из UNIX timestamp.
      Получение текущего момента с временной зоной.
    """

    (ADJ_MINUTE, ADJ_HOUR, ADJ_DAY, ADJ_MONTH, ADJ_YEAR) = range(5)

    FMT_DATE_TIME = "%d.%m.%Y %H:%M"
    FMT_DATE = "%d.%m.%Y"
    FMT_TIME = "%H:%M"
    FMT_DATE_TIME_S = "%d.%m.%Y %H:%M:%S"
    FMT_TIME_S = "%H:%M:%S"

    @classmethod
    def as_none(cls):
        """
          Создает объект, реализующий все методы, но как None.
          В том числе False в bool контексте.
        """
        obj = cls()
        obj.dt = None
        return obj

    def __init__(self, dt=None, tz = None, fmt=None):
        """
          Создание экземпляра. 
          Если dt строка и указан fmt (формат) - разбирается по формату,
            Если не задан fmt - предполагается ISO 8601 формат.
          Если None - текущий момент. число - unix_timestamp.
          Если объект datetime - то он используется.
          Кортеж - то (год, месяц, день, час, мин, сек)
         """
        if tz is None:
            tz = tzlocal()
        if dt is None:
            self.dt = datetime.now(tz)
        elif isinstance(dt, (str,unicode)):
            if fmt:
                self.dt = datetime.strptime(dt,fmt)
                if self.dt.tzinfo is None:
                    self.dt = self.dt.replace(tzinfo=tz)
            else:
                if len(dt) == 17:
                    ts1 = "20%s %s" % (dt[0:6], dt[6:])
                    self.dt = dateutil.parser.parse(ts1)
                else:
                    self.dt = dateutil.parser.parse(dt)
                    if self.dt.tzinfo is None:
                        self.dt = self.dt.replace(tzinfo=tz)
        elif isinstance(dt, (int, long, float)):
            self.dt = datetime.fromtimestamp(dt, tz)  
            if self.dt.tzinfo is None:
                self.dt = self.dt.replace(tzinfo=tz)
        elif isinstance(dt, type(self)):
            self.dt = dt.dt
        elif hasattr(dt, b"__iter__"):
            self.dt = datetime(*dt)
            if self.dt.tzinfo is None:
                self.dt = self.dt.replace(tzinfo=tz)
        else:
            if dt.tzinfo is None:
                self.dt = dt.replace(tzinfo=tz)
            else:
                self.dt = dt

    def to_json(self):
        """
          Конвертирует дату в строку для включения в JSON
        """
        if self.dt is None:
            return None
        else:
            return self.dt.isoformat(b' ')

    def to_ts(self):
        """
          Converts datetime to Unux timestamp
        """
        if self.dt is None:
            return None
            
        return time.mktime(self.dt.timetuple())

    def to_str(self):
        """
          Формирует "строковое" представление даты/времени вида 121023223015+0700
          Как ISO, но короче.
        """
        if self.dt is None:
            return '000000000000+0000'
        else:
            return self.dt.strftime("%y%m%d%H%M%S%z") 

    def to_short(self, fmt=None):
        """
          Формирует "короткое" представление даты/времени.
          Фактически - преобразует дату/время в строку согласно заданному формату fmt
          По умолчанию формат - FMT_DATE_TIME
        """
        if fmt is None:
            fmt = self.FMT_DATE_TIME

        if self.dt is None:
            return ''
        else:
            return self.dt.strftime(fmt) 

    def corr(self, delta, do_clone=False):
        """
          Коррекирует (+) время на указанное количество секунд или временной интервал.
          Что бы уменьшить - вызвать с отрицательным интервалом.
          delta может быть числом (имеются в виду секунды) или timedelta

          Возвращает объект, если do_clone, то копию, иначе самого себя.
        """
        if isinstance(delta, timedelta):
            dt = delta
        else:
            dt = timedelta(seconds = delta)

        if do_clone:
            obj = self.clone()
            obj.corr(delta)
            return obj
        else:
            self.dt = self.dt+dt
            return self

    def adj_to_start(self, what, do_clone=True):
        """
            Скорректировать к началу диапазона
            what::ADJ_ххх
        """
        if do_clone:
            obj = self.clone()
        else:
            obj = self

        dtlist = [obj.dt.year, obj.dt.month, obj.dt.day, obj.dt.hour, obj.dt.minute,
                    obj.dt.second, obj.dt.microsecond, obj.dt.tzinfo]

        dtlist[5] = 0
        dtlist[6] = 0
        if what == self.ADJ_MINUTE:
            pass
        elif what == self.ADJ_HOUR:
            dtlist[4] = 0
        elif what == self.ADJ_DAY:
            dtlist[3] = 0
            dtlist[4] = 0
        elif what == self.ADJ_MONTH:
            dtlist[2] = 1
            dtlist[3] = 0
            dtlist[4] = 0
        elif what == self.ADJ_YEAR:
            dtlist[1] = 1
            dtlist[2] = 1
            dtlist[3] = 0
            dtlist[4] = 0

        obj.dt = datetime(*dtlist)

        return obj

    def adj_to_end(self, what, do_clone=True):
        """
            Скорректировать к началу диапазона
            what::ADJ_ххх
        """
        if do_clone:
            obj = self.clone()
        else:
            obj = self

        dtlist = [obj.dt.year, obj.dt.month, obj.dt.day, obj.dt.hour, obj.dt.minute,
                    obj.dt.second, obj.dt.microsecond, obj.dt.tzinfo]

        dtlist[5] = 59
        dtlist[6] = 1000000-10

        if what == self.ADJ_MINUTE:
            pass
        elif what == self.ADJ_HOUR:
            dtlist[4] = 59
        elif what == self.ADJ_DAY:
            dtlist[3] = 23
            dtlist[4] = 59
        elif what == self.ADJ_MONTH:
            if obj.dt.month == 12:
                next_d = datetime(obj.dt.year+1, 1, 1, 0, 0, 0, 0, obj.dt.tzinfo)
            else:
                next_d = datetime(obj.dt.year, obj.dt.month+1, 1, 0, 0, 0, 0, obj.dt.tzinfo)

            l_d = next_d - timedelta(days = 1)
            print obj.dt, next_d, l_d  

            dtlist[2] = l_d.day
            dtlist[3] = 23
            dtlist[4] = 59
        elif what == self.ADJ_YEAR:
            dtlist[1] = 12
            dtlist[2] = 31
            dtlist[3] = 23
            dtlist[4] = 59

        obj.dt = datetime(*dtlist)

        return obj

    def clone(self):
        """
          Возвращает объект того же класса с теми же данными времени 
        """
        return ZMoment(self.dt)

    def diff(self, other):
        """
            Возвращает разницу в секундах self-other
        """
        mm = self.dt - other.dt
        return mm.total_seconds()

    def __sub__(self, other):
        return self.diff(other)

    def datetime(self):
        return self.dt

    def set_time(self, time, do_clone=False):
        """
            Устанавливает в текущем объекте (или создает новый) время в значение из time::(time, datetime)

            !! Если TZ нового времени отличается от self, то возможна некорректная работа.
            Если time не содержит tz - приводится к текущему
        """
        if time.tzinfo is None:
            time = time.replace(tzinfo=self.dt.tzinfo)
        else:
            time = time.astimezone(self.dt.tzinfo)

        ndt = self.dt.replace(hour = time.hour, minute=time.minute, second=time.second)
        if do_clone:
            return type(self)(ndt)
        else:
            self.dt = ndt
            return self

    def is_none(self):
        return self.dt is None

    def __cmp__(self, other):
        """
        """
        ds = self.dt
        if isinstance(other, ZMoment):
            do = other.dt
        elif isinstance(other, datetime):
            do = other
        else:
            do = None
        if ds==do:
            return 0
        elif ds<do:
            return -1
        else:
            return 1

    def __str__(self):
        if self.dt is None:
            return b''
        else:
            return self.dt.isoformat(b' ')

    def __unicode__(self):
        if self.dt is None:
            return u''
        else:
            return unicode(self.dt.isoformat(b' '))

    def __repr__(self):
        return repr(self.dt)

    def __nonzero__(self):
        if self.dt is None:
            return False
        else:
            return True


def strip_sign(val, sign=+1):
    """
      Если val - текстовая строка, убирает пробелы с начала и конца,
      Если val - числовое - меняет его знак, если sign<0
      иначе возвращает как есть.
    """
    if hasattr(val, 'strip'):
        return val.strip(' ')
    elif isinstance(val, numbers.Number):
        return -val if sign<0 else val


class ExtOrderedDict(OrderedDict):
    """
      Добавляет к обычному OrderedDict возможность получать элементы
      как атрибуты экземпляра, а так же по их порядковому номеру.
    """

    @classmethod
    def init_unpack(cls, arr, func=None):
        """
          Инициализирует словарь из списка списков arr, выделяя первый элемент элементов
          списка в ключ, а остальные передавая в func, что бы получить значение.
          При подстановке элементы "распаковываются" в порядковые параметры.
          Если func = None, то создается простой tuple
        """
        if func is None:
            return cls([(itm[0], tuple(itm[1:])) for itm in arr])
        else:
            return cls([(itm[0], func(*(itm[1:]))) for itm in arr])

    def __getitem__(self, itm):
        if isinstance(itm, numbers.Integral):
            return self[self.keys()[itm]]
        else:
            return super(ExtOrderedDict,self).__getitem__(itm)

    def __getattr__(self, attr):
        """

        """
        if attr in self:
            return self[attr]
        else:
            raise AttributeError("'%s' is not a correct attribute." % (attr,))


class JSDict(dict):
    """
      Добавляет к обычному dict возможность получать элементы
      как атрибуты экземпляра.
      Атрибуты задаются как обычно или именоваными параметрами в конструкторе
    """

    _FIELDS = None

    @classmethod
    def custom_class(cls, cls_name, *args):
        """
            Создает новый класс, наследник от существующего.
            в args можно передать 1 или 2 аргумента. Если параметра 2, то первый - docstring,
            другой параметр - перечень возможных полей (FIELDS).
            Если FIELDS список - то поля - значения списка, значения по умолчанию - None.
            Если FIELDS словарь, то имена полей - значения ключей, значения - будут поставлены по умолчанию при озданиии нового экземпляра.
        """
        if len(args)==2 and isinstance(args[0], (str, unicode)):
            docstring = args[0]
            FIELDS = args[1]
        elif len(args)==1:
            FIELDS = args[0]
        else:
            FIELDS = None

        if FIELDS is None:
            flds = None
        elif isinstance(FIELDS, Mapping):
            flds = FIELDS
        elif isinstance(FIELDS, Iterable):
            flds ={}
            for itm in FIELDS:
                flds[str(itm)] = None
        else:
            raise Exception("Uncorrect type for FIELDS.")

        return type(cls_name, (cls,), {"_FIELDS": flds})

    def __init__(self, *args, **kwargs):
        """
        """
        super(JSDict, self).__init__(*args, **kwargs)
        flds = getattr(self, "_FIELDS", None)
        if flds is None:
            return

        for key, val in flds.iteritems():
            if key in self:
                continue
            self[key] = val

    def __getattr__(self, attr):
        """

        """
        if attr in self:
            return self[attr]
        else:
            #return getattr(self, attr)
            if hasattr(self, attr):
                return getattr(self, attr)
            else:
                raise AttributeError("'%s' is not a correct attribute." % (attr,))

    def __setattr__(self, attr, val):
        """

        """
        self[attr]=val
        return
        
        if attr in self:
            self[attr]=val
        else:
            raise AttributeError("'%s' is not a correct attribute." % (attr,))


def unicode_repr(arg):
    """
      Возвращает unicode строку, являющююся преобразовнным str представленим arg
    """
    return str(arg).decode('raw_unicode_escape') #Если исходные строки - unicode


def load_class(path, base=None):
    """
        Загружает (импортирует) и возвращает класс (функцию), заданный строкой - путем path.
        Путь указывается через "." от корня проекта (как модули Python)
        Если задан base - добавляется в начало.
    """
    import importlib

    mm, dd, cls_name = path.rpartition(".")
    mm = mm.lstrip(".")
    if base:
        base = base.strip(".")
        mname = ".".join((base, mm))
    else:
        mname = mm
    module = importlib.import_module(mname)
    return getattr(module, cls_name)


class MatrixBuffer(object):
    """
      Объект позволяет размещатьи получать данные из 2х мерной матрицы,
      обращаясо по координате (row, col).
      Размер матрицы определяетсмя динамически исходя из размещенных данных.
      свойства rows_count и cols_count возвращают текущий размер.
      none_val - заполнитель пустых ячеек, если они не были заполнены, при выдачи матрицей.
    """

    def __init__(self, none_val=None):
        """
        """
        self.none_val = none_val
        self.row_idx = {}
        self._max_row = -1
        self._max_col = -1

    @property
    def rows_count(self):
        return self._max_row + 1

    @property
    def cols_count(self):
        return self._max_col + 1

    def put(self, row, col, val):
        """
          Поместить значение в матрицу.
        """
        r = self.row_idx.get(row, None)
        if r is None:
            r = {}
            self.row_idx[row]=r
        r[col]=val    
        if self._max_row<row:
            self._max_row=row
        if self._max_col<col:
            self._max_col=col

    def get(self, row, col):
        """
          Возвращает значение из матрицы или none_valе сли его нет
        """
        r = self.row_idx.get(row, None)
        if r is None:
            return self.none_val
        return r.get(col, self.none_val)    

    def has(self, row, col):
        """
          Проверяет, заполнена ли ячейка значением
        """
        r = self.row_idx.get(row, None)
        if r is None:
            return False
        v =  r.get(col, None)
        return v is not None    


class ConstDict(object):
    """
      Словарь констант с расшифровками.
      Инициализируется списком кортежей из строк:
        (<Имя_константы>,<Расшифровка>)
      Плучить значение можно, использовав имя константы в качестве атрибута объекта.
      Получить расшифровку - <Имя_константы>__display или get_display(имя)

      Получить значения в виде списка кортежей (id,<Расшифровка> ) можно с помощью метода
        get_choices()

      Что бы не было конфликта имен имена констант приводятся к большим буквам

    """
    POSTFIX = "__display"

    def __init__(self, lst):
        """
          lst список кортежей (<Имя_константы>,<Расшифровка>)
        """
        self._keys = []
        self._keysd = {}
        self._vals = []

        for no, itm in enumerate(lst):
            self._keys.append(itm[0])
            self._keysd[itm[0]] = no
            self._vals.append(itm[1])

    def __getattr__(self, attr):
        """
          Возвращает числовое значение атрибута - ключа,
          если к названию ключа добавлено __display - возвращает описание 
        """
        rr = attr.partition(self.POSTFIX)
        key = rr[0]
        no = self._keysd.get(key,None)
        if no is None:
            raise AttributeError("'%s' is not a correct attribute." % (attr,))
        else:
            if rr[1] == self.POSTFIX and rr[2]=='':
                return self._vals[no]
            else: 
                return no

    def get_choices(self):
        """
          Возвращает список кортежей (<no>, <Расшифровка>), 
            <no> - цифровое значение константы
        """
        return tuple([(no, self._vals[no]) for no, itm in enumerate(self._keys)])


def strtime_to_date(strtime):
    """Преобразует строчное время('12:30') в datetime с сегодняшней датой"""
    hour, minute = strtime.split(':')
    date = datetime.now().replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
    return date


def split_list(l, n):
    """
        Разбивает список l на отрезки по n элементов
        l: <list> or <tuple> or <str>
        n: <int>
        Возвращает список
    """
    return zip(*[iter(l)] * n)


class DecimalEncoder(json.JSONEncoder):
    """
        Костыль для JSON. Иначе он не сериализует decimal.
        Используется в json.dumps:
            json.dumps(data, cls=DecimalEncoder)
    """
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


def to_hex_str(inp):
    """
      Преобразует массив байтов в текстовую строку, в которой байты представлены
      парой шестнадцатеричных знаков через запятую
    """
    inp = bytearray(inp)
    return ','.join(['{:02X}'.format(i) for i in inp])


def to_bytearray(inp_str):
    """
      Преобразует строку в которой байты заданы 2мя шестнадцатеричными цифрами ч/з запятую
      в bytearray
    """
    return bytearray([int(i,16) for i in inp_str.split(',')])


def lon_to_str(coord, none_val = ""):
    """
      Форматирование числовой координаты - длготы в строку.

    """
    if coord is None:
        return none_val
    if coord <0:
        sg = 'W'
        coord = - coord
    else:
        sg = 'E'
    hd = int(coord)
    coord = (coord - hd)*60
    mm = int(coord)
    coord = (coord - mm)*60
    ss = int(coord)

    return "{:s}{:03d}.{:02d}.{:02d}".format(sg, hd, mm, ss)

def lat_to_str(coord, none_val = ""):
    """
      Форматирование числовой координаты - широты в строку.

    """
    if coord is None:
        return none_val
    if coord <0:
        sg = 'S'
        coord = - coord
    else:
        sg = 'N'
    hd = int(coord)
    coord = (coord - hd)*60
    mm = int(coord)
    coord = (coord - mm)*60
    ss = int(coord)

    return "{:s}{:03d}.{:02d}.{:02d}".format(sg, hd, mm, ss)

def text_to_lonlat(txt, txt_latlon=True, to_lonlat=True):
    """
      Преобразовывает строку из пары float чисел в кортеж чисел (lon, lat)
      Если txt_latlon==True, то предполагается в строке "lat,lon", иначе наоборот.
      Если to_lonlat==True, то результат (lon, lat), иначе (lat, lon)
      Если ошибка преобразований - возвращает (None,None,)
    """
    lat = None
    lon = None

    ptxt = txt.partition(",")
    try:
        f0 = float(ptxt[0])
    except Exception as e:
        return (None,None,)

    try:
        f1 = float(ptxt[2])
    except Exception as e:
        return (None,None,)

    if txt_latlon:
        lat = f0
        lon = f1
    else:
        lon = f0
        lat = f1

    if to_lonlat:
        return (lon,lat)
    else:
        return (lat,lon)
        

def as_dict(arg, limit=None):
    """
        Позволяет доступаться к аргументам arg как к элементам словаря.
        Позвращает прокси объект, реализующий доступ через __getitem__
        limit - ограниченный список имен атрибутов. Если None - то все.
    """

    class dict_proxy(Mapping):
        """
        def __init__(self, arg, limit):
            self.arg = arg
            self.limit = limit
        """

        def __getitem__(self, itm):
            if limit and itm not in limit:
                raise KeyError("Unaccessed argument '{}'".format(itm))
            return getattr(arg, itm)

        def __iter__(self):
            for key in self.keys():
                yield key

        def __len__(self):
            return len(self.keys())

        def __contains__(self, key):
            return key in self.keys()

        def keys(self):
            if limit:
                return limit
            else:
                return dir(arg)

        def items(self):
            for key in self.keys():
                yield (key, getattr(arg, key, None))

        def values(self):
            for key in self.keys():
                yield getattr(arg, key, None)

        def get(self, default=None):
            if limit and itm not in limit:
                raise KeyError("Unaccessed argument '{}'".format(itm))
            return getattr(arg, itm, default)

        def __eq__(self, other):
            return arg == other

        def __ne__(self, other):
            return arg != other


    return dict_proxy()

