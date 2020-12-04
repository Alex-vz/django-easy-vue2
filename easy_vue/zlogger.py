# -*- coding: utf-8 -*-

from __future__ import unicode_literals

"""
   Упрощенный логгер.
   Позволяет кастомизировать и отсекать сообщения по уровням.
   Нужен, например для Джанго, что бы не заморачиваться со сложными настройками. 
   Или использовать свои уровни логгирования.
   Способен ретранслировать сообщения в обычный логгер.

   По умолчанию просто печатает сообщения на терминал с добавлением полей заголовков.
"""

from .lib import ZMoment

ZL_CRITICAL = 50
ZL_ERROR = 40
ZL_WARNING = 30
ZL_INFO = 20
ZL_DEBUG = 10
ZL_NOTSET = 0


class ZLogger(object):
    """
        Клас, эмулирующий logger. Что бы не замарачиваться в настоящим логгером
        в Django. а потом переделать, если нужно.

        Пока делает print, добавляя общий заголовок.

        Порядок подготовки сообщения:
        - сначала берется пользовательское msg_pattern и обрабатывается с помощью .format
             и словарем, состоящим из стандарнтых ключей и дополнительных пользователя.
        потом аналогично обрабатывается строка формата лога, в ключ message подставляется результат прошлого этапа.
    """

    DEFAULT_FORMAT=u"{loglevel}:{moment}: {message}"


    LEVELS={  #<уровень>: (<текст в лог>, <имя функции>),
        ZL_CRITICAL: ("CRITICAL", "critical"),
        ZL_ERROR: ("ERROR", "error"),
        ZL_WARNING: ("WARNING", "warning"),
        ZL_INFO: ("INFO", "info"),
        ZL_DEBUG: ("DEBUG", "debug"),
        ZL_NOTSET: ("NOSET", None),
        }


    def __init__(self, loglevel=None, logger = None, log_format=None):
        """
            loglevel
            logger - настроенный стандартный логгер. Если задан - вывод бедет передан в него.
        """
        if loglevel is None:
            self.loglevel = ZL_ERROR
        else: 
            self.loglevel = loglevel 
        self.logger = logger
        if log_format is None:
            self._format = self.DEFAULT_FORMAT
        else:
            self._format = log_format

    def _proc_message(self, level, msg_pattern, kwargs):
        """
        """
        if level < self.loglevel:
            return

        kw = {"loglevel":self.LEVELS[level][0], "moment":str(ZMoment())}
        kw.update(kwargs)
        #msg = msg_pattern.format(**kw)
        msg = msg_pattern
        kw["message"] = msg
        print self._format.format(**kw)

    def error(self, msg_pattern, **kwargs):
        self._proc_message(ZL_ERROR, msg_pattern, kwargs)

    def debug(self, msg_pattern, **kwargs):
        self._proc_message(ZL_DEBUG, msg_pattern, kwargs)

    def info(self, msg_pattern, **kwargs):
        self._proc_message(ZL_INFO, msg_pattern, kwargs)

    def critical(self, msg_pattern, **kwargs):
        self._proc_message(ZL_CRITICAL, msg_pattern, kwargs)

    def warning(self, msg_pattern, **kwargs):
        self._proc_message(ZL_WARNING, msg_pattern, kwargs)


class ZLoggerAdapter(object):

    def __init__(self, logger, extra=None):
        """
            Returns an instance of ZLoggerAdapter initialized with an underlying 
            ZLogger instance and a dict-like object.
        """
        self.logger = logger
        if extra is None:
            self.extra = {}
        else:
            self.extra = extra

    def process(self, msg_pattern, kwargs):
        """
            Modifies the message and/or keyword arguments passed to a logging call
            in order to insert contextual information. 
            This implementation takes the object passed as extra to the constructor 
            and adds it to kwargs using key ‘extra’. 
            The return value is a (msg, kwargs) tuple which has the (possibly modified) 
            versions of the arguments passed in.
        """
        return (msg_pattern, kwargs)

    def _proc_message(self, level, msg_pattern, kwargs):
        """
        """
        kw = kwargs.copy()
        msg, kw = self.process(msg_pattern, kw)
        kw.update(self.extra)
        getattr(self.logger, ZLogger.LEVELS[level][1])(msg, **kw)

    def error(self, msg_pattern, **kwargs):
        self._proc_message(ZL_ERROR, msg_pattern, kwargs)

    def debug(self, msg_pattern, **kwargs):
        self._proc_message(ZL_DEBUG, msg_pattern, kwargs)

    def info(self, msg_pattern, **kwargs):
        self._proc_message(ZL_INFO, msg_pattern, kwargs)

    def critical(self, msg_pattern, **kwargs):
        self._proc_message(ZL_CRITICAL, msg_pattern, kwargs)

    def warning(self, msg_pattern, **kwargs):
        self._proc_message(ZL_WARNING, msg_pattern, kwargs)


