# -*- coding: utf-8 -*-

"""
    RESTful easy Django extension.
    Definition classes, use for parse and validate incoming request parameters.
"""

from __future__ import unicode_literals

import json

from django.apps import apps as django_apps


class EUncorrectDefenition(Exception):
    """
        Ошибка неправильного определения
    """


class EParseError(Exception):

    def __init__(self, u_msg, detail=None, *args, **kwargs):
        """
           u_msg -- unicode текст ошибки.
           detail -- произвольный dict с дополнительной информацией по ошибке. 
        """
        super(EParseError, self).__init__(self, u_msg, *args, **kwargs)
        
        self.u_msg = u_msg
        self.detail = detail



class EParamNotFound(EParseError):
    """
        Вариант для обозначения отсутствия параметра.
    """


class IncomingParamBase(object):
    """
        При создании экземпляра класса описывается имя входящего параметра из request
        и имя атрибута объекта результата.

        Для разбора 
        В случае ошибки парсинга возвращает EParseError
    """

    def __init__(self, param_id, to_attribute=None, param_label=None, 
        required=True, do_multy=False, **kwargs):
        """
            do_multy -- разбирать все значения с таким именем, результат будет всегда список.
                Если False - то только первое значение. Резултат - значение ожидаемого типа.
        """

        self.param_id = param_id 

        if to_attribute is None:
            self.to_attribute = param_id
        else:
            self.to_attribute = to_attribute
        
        if param_label is None:
            self.param_label = param_id
        else:
            self.param_label = param_label

        self.do_multy = do_multy
        self.required = required

    def parse(self, request_dict, result=None):
        """
            Вызывается для разбора входящих параметров.
                request_dict -- словарь с входящими параметрами
                res -- объект, куда будет дописано рабобраное значение
        """

        if self.param_id not in request_dict:
            if self.required:
                raise EParamNotFound(self.error_text(u"не найден"))
            else:
                if self.do_multy:
                    vv = []
                else:
                    vv = None

                result[self.to_attribute] = vv
                return

        if self.do_multy:
            vv=[]
            for itm in request_dict.getlist(self.param_id):
                vv.append(self._parse_itm(itm))
        else:
            vv = self._parse_itm(request_dict[self.param_id])
            try:
                vv = self.do_parse(request_dict[self.param_id])
            except EParseError as e:
                raise e
            except Exception as e:
                raise EParseError(self.error_text(str(e)))

        if result is not None:
            result[self.to_attribute] = vv

        return vv

    def do_parse(self, in_value):
        """
            Собственно разбор. Возвращает разобранное значение.
            Определяется в потомках
        """
        return in_value

    def do_check(self, value):
        """
            Проверяет корректность значения после преобразования.
            Возвращает текст ошибки или None - все корректно.

            Переопределяется в потомках. 
        """

    def _parse_itm(self, in_value):
        """
            Разбирает один эелемент из входящих данных
        """
        try:
            vv = self.do_parse(in_value)
        except EParseError as e:
            raise e
        except Exception as e:
            raise EParseError(self.error_text(str(e)))

        err = self.do_check(vv)
        if err:
            raise EParseError(self.error_text(str(e)))

        return vv

    def error_text(self, err_msg):
        """
        """
        return u"'{}' {}.".format(self.param_label, err_msg)


class CommaListParam(IncomingParamBase):
    """
        Значение параметра - строка, представляющся список одинаковых значений через ",".
        тип значения передается при инициализации в атрибуте param_class 
        в виде настроенного экземпляра класса от IncomingParamBase
    """

    def __init__(self, param_object, separator=","):
        """
           param_object - экземпляр класса от IncomingParamBase, определяющий тип
           и атрибуты разбора параметра.
           Результат - всегда список с типом, возвращаемым param_object.
        """
        self.param_object = param_object
        self.param_object.do_multy = False
        self.separator = separator

        self.param_id = self.param_object.param_id 
        self.to_attribute = self.param_object.to_attribute
        self.param_label = self.param_object.param_label

        self.do_multy = False

    def do_parse(self, in_value):
        """
            Собственно разбор. Возвращает разобранное значение.
            Определяется в потомках
        """
        lst = in_value.split(self.separator)
        res=[]
        for itm in lst:
            vv = self.param_object.parse({self.param_id: itm}, None)
            res.append(vv)

        return res


#====

class UnicodeParam(IncomingParamBase):
    """
    """

    def do_parse(self, in_value):
        """
            Собственно разбор. Возвращает разобранное значение.
            Определяется в потомках
        """
        return unicode(in_value)


class IntParam(IncomingParamBase):
    """
        Целое.
        Доп атрибуты: 
            min_val, max_val, -- диапазон включая условие,
            ex_min_val, ex_max_val -- диапазон исключая границы. Это условие главное.
    """

    def __init__(self, *args, **kwargs):
        """
        """
        super(IntParam, self).__init__(*args, **kwargs)
        
        self.min_val = kwargs.get("min_val") 
        self.max_val = kwargs.get("max_val")
        self.ex_min_val = kwargs.get("ex_min_val") 
        self.ex_max_val = kwargs.get("ex_max_val")

    def do_parse(self, in_value):
        """
            Собственно разбор. Возвращает разобранное значение.
            Определяется в потомках
        """
        try:
            res = int(in_value)
        except Exception as e:
            raise EParseError(self.error_text(u"некорректный формат"))

        return res

    def do_check(self, value):
        """
            Проверяет корректность значения после преобразования.
            Возвращает текст ошибки или None - все корректно.

            Переопределяется в потомках. 
        """

        if self.ex_min_val is not None and value <= self.ex_min_val:
            return u"Значение больше минимального"
        if self.ex_max_val is not None and value >= self.ex_max_val:
            return u"Значение меньше максимального"
        if self.min_val is not None and value < self.min_val:
            return u"Значение больше минимального"
        if self.max_val is not None and value > self.max_val:
            return u"Значение меньше максимального"


class IdParam(IncomingParamBase):
    """
        Целое, больше 0
    """

    def do_parse(self, in_value):
        """
            Собственно разбор. Возвращает разобранное значение.
            Определяется в потомках
        """
        try:
            res = int(in_value)
        except Exception as e:
            raise EParseError(self.error_text(u"некорректный формат"))

        if not res>0:
            raise EParseError(self.error_text(u"некорректное значение"))

        return res


class ModelParam(IncomingParamBase):
    """
        Параметр - id экземпляра модели.
        Значение - экземпляр модели

        Класс модели указывается при инициализации в атрибуте model.
            model  может быть и класс, и название класса в виде "application.model"
            Так же можно указать другое имя поля для поиска в атрибуте field 
    """

    def __init__(self, *args, **kwargs):
        super(ModelParam, self).__init__(*args, **kwargs)

        try:
            model = kwargs['model']
        except Exception as e:
            raise EUncorrectDefenition(u"Необходимо указать класс модели")

        self.pk = kwargs.get("field", "pk")

        if isinstance(model, (str, unicode)):
            try:
                model = django_apps.get_model(model)
            except Exception as e:
                raise EUncorrectDefenition(u"Некорректное имя класса модели")

        self.model = model

    def do_parse(self, in_value):
        """
            Собственно разбор. Возвращает разобранное значение.
            Определяется в потомках
        """

        try:
            return self.model.objects.get(**{self.pk: in_value})
        except self.model.DoesNotExist as e:
            raise EParseError(self.error_text(u"Объект не найден"))
        except Exception as e:
            raise EParseError(self.error_text(u"Некорректный ID объекта"))


class JSONParam(IncomingParamBase):
    """
        Целое, больше 0
    """

    def do_parse(self, in_value):
        """
            Собственно разбор. Возвращает разобранное значение.
            Определяется в потомках
        """
        try:
            res = json.loads(in_value)
        except Exception as e:
            raise EParseError(self.error_text(u"некорректный формат"))

        return res


