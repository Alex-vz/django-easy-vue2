#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Date    : 2017-02-21 09:51:10
# @Author  : Your Name (you@example.org)
# @Link    : http://example.org
# @Version : $Id$

from __future__ import unicode_literals

"""
  Общие утилиты для работы с Django.


  JSONPostMixin

  TemplatePostMixin

  TextPostMixin

"""

import json
import collections

from .lib import ExtOrderedDict, load_class
from .lib import JSDict

from django.db import models
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import Http404, JsonResponse, FileResponse, HttpResponse, HttpResponseRedirect
from django.views.generic.base import ContextMixin, TemplateView, View


class WithConstsMixin(ContextMixin):
    """
      Добовляет в контекст параметр 'consts' - словарь констант.
      Словарь указывается в атрибуте класса `consts`

      Добавлять с определении класса слева от базовых View классов.
    """

    def get_context_data(self, **kwargs):
        """
          Добавляет 'consts' с константами:
        """
        context = super(WithConstsMixin, self).get_context_data(**kwargs)
        if hasattr(self, 'consts'):
            context['consts'] = self.consts
        return context


class LoginRequiredMixin(object):
    login_url=None

    @classmethod
    def as_view(cls, **initkwargs):
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        return login_required(login_url= cls.login_url)(view)


class CsrfEnsureMixin(object):
    """
      Гарантирует наличие кука ключа CSRF в выдаче. 
      В стандартном поведениии этого ключа может и не быть, если не используется FormView,
        то есть с AJAX запросами такая проблемма весьма актуальна.
    """
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(CsrfEnsureMixin, cls).as_view(**initkwargs)
        return ensure_csrf_cookie(view)


class JSONViewBase(View):
    """
      Читает данные из POST, содержащие поля с JSON выражениями.
      
      Создает в форме атрибут post_data::ExtOrderedDict 
        с атрибутами - именами полей и расшифрованными значениями.

      Перед этим миксином должна быть определена обработка post запроса.

      Предпологается, что в представление был передан POST запрос, в котором элементы 
        содержат значения, закодированные через JSON.
      Список имен читаемых полей - в атрибуте класса json_fields.
      Атрибут ajax_only со списком имен методов 'get', 'post' вызывает ошибку 404, 
      если представление было вызвано через этот метод не через AJAX

      Добавляется в определение класса слева от стандартных View и ..PostMixin иэ этого модуля.

    """
    post_data=None
    json_fields=[]

    def read_POST(self):
        """
        Читает POST, создает post_data
        """
        self.post_data=ExtOrderedDict()
        for itm in self.json_fields:
            val_j = self.request.POST.get(itm, None)
            val = None
            if val_j:
                try:
                    val = json.loads(val_j)
                except Exception as e:
                    print "Exception:: ", unicode(e)
                    print
                    pass
            self.post_data[itm] = val

    def post(self, request, *args, **kwargs):
        """
        """
        self.read_POST()
        return super(JSONViewBase, self).post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """
        """
        self.post_data = None
        return super(JSONViewBase, self).get(request, *args, **kwargs)


class PostViewMixin(View):
    """
      Реализует метод post к обычному View.

      Возвращаемое значение генерируется в методе get_output_data.
      В потомках можно переопределить метод prepare_response, для преобразования 
        формата вывода get_output_data в нужный тип.
      По умолчанию - передает в HTTPResponse как есть.

      Определяет атрибут: 
        request_params равный request.post или get в завимости от метода.
      
      Атрибуты класса для настройки:
        http_method_names=['get', 'post'] - варианты разрешенных обработчиков
        ajax_only=false - если true, то будет разрешен только AJAX вызов
        registered_only - Если true, то вызов разрешен только зарегистрированным 
            пользователям. Иначе вызывается get_forbidden_data(no_login, no_perms), что
            бы получить JSON структуру и вернуть ее.
            Если нужно вызвать исключения - это можно сделать в get_forbidden_data.
            По умолчанию исключения не вызываются. 
            Там же можно указать статус код выхода. 
        active_only - Проверять ли активность пользователя.
        permissions - список названий разрешений, требуемых у пользователя для доступа.
            Все перечисленные разрешения должны присутствовать одновременно.
            Для проверки вызывает check_user_permissions, который может быть переопределен.
            Работает только с registered_only=True.
            Если permissions is None - разрешения не проверяются.


      Использование:
        class MyView(PostViewMixin, View)

    """

    http_method_names=['get', 'post']

    ajax_only=False
    registered_only=False
    active_only=True
    permissions = None

    def get_output_data(self, request, *args, **kwargs):
        """
            Метод виртуальный. Переопределяется в потомках.
        """
        return ""

    def prepare_response(self, out_data):
        """
            Может переопределяться в потомках.
        """
        return HttpResponse(out_data)

    def get_forbidden_data(self, request, no_login, no_perms, *args, **kwargs):
        """
          Вызывается перед возвратом JSON, если были нарушены требования 
            регистрации пользователя или не хватает прав
        """
        if no_login:
            return {"Error":"Login required."}
        if no_perms:
            return {"Error":"Permission required."}
        return {"Error":"Some error."}

    def check_user_permissions(self, user, permissions = None ):
        """
          Проверяет, что бы для пользователя были разрешены все разрешения, перечисленные
            в self.permissions.
          Возвращает True, если это так, или self.permissions is None.
          Если пользователь не авторизован - возвращает False

        """
        if not user.is_authenticated():
            return False
        if permissions is None:
            permissions = self.permissions
        if permissions is None:
            return True
        if len(permissions) is None:
            return False
        res = True
        for itm in permissions:
            if not user.has_perm(itm):
                res = False
        return res

    def check_user_authenticated(self, request, *args, **kwargs):
        """
          Проверяет пользователя и права, генерирует выдачу JSON.
          При ошибке - получает дланные из get_forbidden_data и выдает выдачей.
        """
        if self.registered_only:
            if request.user.is_authenticated() and (request.user.is_active or not self.active_only):
                if self.check_user_permissions(request.user):
                    return self.proc_view(request, *args, **kwargs)
                else:
                    return JsonResponse(self.get_forbidden_data(request,True, True, *args, **kwargs))                
            else:
                return JsonResponse(self.get_forbidden_data(request,True, None, *args, **kwargs))                
        else:
            return self.proc_view(request, *args, **kwargs)

    def proc_view(self, request, *args, **kwargs):
        """
          Запрашиваются данные в get_output_data, и возвращаются в JsonResponse
          Может дополнятся в потомках для стандартных предобработок данных.
        """
        return self.prepare_response(self.get_output_data(request, *args, **kwargs), request, *args, **kwargs)
        #return JsonResponse(self.get_output_data(request, *args, **kwargs))

    def post(self, request, *args, **kwargs):
        """
        """
        if ('post' in self.http_method_names) and ((self.ajax_only and self.request.is_ajax()) or not self.ajax_only ):
            self.request_params = request.POST
            "check_user_authenticated"
            return self.check_user_authenticated(request, *args, **kwargs)
        else:
            raise Http404('Method unallowed')

    def get(self, request, *args, **kwargs):
        """
        """
        if ('get' in self.http_method_names) and ((self.ajax_only and self.request.is_ajax()) or not self.ajax_only):
            self.request_params = request.GET
            return self.check_user_authenticated(request, *args, **kwargs)
        else:
            raise Http404('Method unallowed')


class JSONPostMixin(View):
    """
      Реализует метод post, возвращающий JsonResponse.
      Возвращаемое значение в виде словаря генерируется в методе get_output_data.

      Определяет атрибут: 
        request_params равный request.post или get в завимости от метода.
      
      Атрибуты класса для настройки:
        http_method_names=['get', 'post'] - варианты разрешенных обработчиков
        ajax_only=false - если true, то будет разрешен только AJAX вызов
        registered_only - Если true, то вызов разрешен только зарегистрированным 
            пользователям. Иначе вызывается get_forbidden_data(no_login, no_perms), что
            бы получить JSON структуру и вернуть ее.
            Если нужно вызвать исключения - это можно сделать в get_forbidden_data.
            По умолчанию исключения не вызываются. 
            Там же можно указать статус код выхода. 
        active_only - Проверять ли активность пользователя.
        permissions - список названий разрешений, требуемых у пользователя для доступа.
            Все перечисленные разрешения должны присутствовать одновременно.
            Для проверки вызывает check_user_permissions, который может быть переопределен.
            Работает только с registered_only=True.
            Если permissions is None - разрешения не проверяются.


      Использование:
        class MyView(JSONPostMixin, View)

    """

    http_method_names=['get', 'post']

    ajax_only=False
    registered_only=False
    active_only=True
    permissions = None

    def get_output_data(self, request, *args, **kwargs):
        """
        """
        return {}

    def get_forbidden_data(self, request, no_login, no_perms, *args, **kwargs):
        """
          Вызывается перед возвратом JSON, если были нарушены требования 
            регистрации пользователя или не хватает прав
        """
        if no_login:
            return {"Error":"Login required."}
        if no_perms:
            return {"Error":"Permission required."}
        return {"Error":"Some error."}

    def check_user_permissions(self, user, permissions = None ):
        """
          Проверяет, что бы для пользователя были разрешены все разрешения, перечисленные
            в self.permissions.
          Возвращает True, если это так, или self.permissions is None.
          Если пользователь не авторизован - возвращает False

        """
        if not user.is_authenticated():
            return False
        if permissions is None:
            permissions = self.permissions
        if permissions is None:
            return True
        if len(permissions) is None:
            return False
        res = True
        for itm in permissions:
            if not user.has_perm(itm):
                res = False
        return res

    def check_user_authenticated(self, request, *args, **kwargs):
        """
          Проверяет пользователя и права, генерирует выдачу JSON.
          При ошибке - получает дланные из get_forbidden_data и выдает выдачей.
        """
        if self.registered_only:
            if request.user.is_authenticated() and (request.user.is_active or not self.active_only):
                if self.check_user_permissions(request.user):
                    return self.proc_view(request, *args, **kwargs)
                else:
                    return JsonResponse(self.get_forbidden_data(request,True, True, *args, **kwargs))                
            else:
                return JsonResponse(self.get_forbidden_data(request,True, None, *args, **kwargs))                
        else:
            return self.proc_view(request, *args, **kwargs)

    def proc_view(self, request, *args, **kwargs):
        """
          Запрашиваются данные в get_output_data, и возвращаются в JsonResponse
          Может дополнятся в потомках для стандартных предобработок данных.
        """
        return JsonResponse(self.get_output_data(request, *args, **kwargs))

    def post(self, request, *args, **kwargs):
        """
        """
        if ('post' in self.http_method_names) and ((self.ajax_only and self.request.is_ajax()) or not self.ajax_only ):
            self.request_params = request.POST
            return self.check_user_authenticated(request, *args, **kwargs)
        else:
            raise Http404()

    def get(self, request, *args, **kwargs):
        """
        """
        if ('get' in self.http_method_names) and ((self.ajax_only and self.request.is_ajax()) or not self.ajax_only ):
            self.request_params = request.GET
            return self.check_user_authenticated(request, *args, **kwargs)
        else:
            raise Http404()


class TemplatePostMixin(TemplateView):
    """
      Реализует метод post, генерирующий обычный TemplateResponce.
      стандартный TemplateView метод POST не реализует.
      Удобно использовать в AJAX запросах, которые вызываются по post и возвращают 
        готовый HTML, сформированный с шаблоном.

      Атрибуты класса
        ajax_only=false - если true, то будет разрешен только AJAX вызов

      Использование:
        class MyView(TemplatePostMixin, TemplateView)
    """
    ajax_only=False

    def post(self, request, *args, **kwargs):
        """
        """
        if ((self.ajax_only and self.request.is_ajax()) or not self.ajax_only ):
          context = self.get_context_data(**kwargs)
          return self.render_to_response(context)
        else:
          raise Http404()


class TextPostMixin(View):
    """
      Реализует метод post, возвращающий простой текст.
      Возвращаетмое значение в виде unicode строки генерируется в методе get_output_text
      Используется для возврата предформатированных данных (Google JSON DataTable например)

      Атрибуты класса
        ajax_only=false - если true, то будет разрешен только AJAX вызов

      Использование:
        class MyView(TextPostMixin, View)
    """
    ajax_only=False

    def get_output_text(self, request, *args, **kwargs):
        """
        """
        return ""

    def post(self, request, *args, **kwargs):
        """
        """
        if ((self.ajax_only and self.request.is_ajax()) or not self.ajax_only ):
          return HttpResponse(unicode(self.get_output_text(request, *args, **kwargs)),
               content_type='text/plain')
        else:
          raise Http404()


class JSONPostMixin_1(PostViewMixin, View):
    """
        !! Вместо JSONPostMixin. Нужно проверить.
        Предполагает, что get_output_data - словарь данных,
        которые передает в виде HJSONResponse
    """

    def get_output_data(self, request, *args, **kwargs):
        """
            Метод виртуальный. Переопределяется в потомках.
        """
        return {}

    def prepare_response(self, out_data, request, *args, **kwargs):
        """
           JsonResponse(out_data) 
        """
        return JsonResponse(out_data)


class EJSONMixinErrorException(Exception):
    """
        Специальное исключение, индицирующее, что в обработке была выявлена ошибка,
        и записана в ответ.
    """
    pass 


class JSONAnswerMixin(JSONPostMixin_1):
    """
        Миксин, собирающий "ответ" (словарь данных для выдачи в JSON), 
        в том числе поля 'answer' = "success"|"error" и поле "error"

        Реализует валидацию входных параметров используя Form.
        Класс формы задается в PARAMS_FORM_CLASS. Если None - валидация не осуществляется.
        Валидированные и преобразоыванные параметры помещаются в cleaned_params::JSDict.
        Если вализация не прошла  вормируется ответ с error.

        Можно установить CLEAN_RAISE_ERROR = False, тогда не будет формироваться состояние
        и исключение ошибки, но будет сформирован атрибут self.input_errors = form.errors 
    """

    PARAMS_FORM_CLASS = None
    CLEAN_RAISE_ERROR = True

    ANSWER_SUCCESS_VAL = "success"
    ANSWER_ERROR_VAL = "error"
    ANSWER_ANSWER_KEY = "answer"
    ANSWER_ERROR_KEY = "error"
    
    def process(self, request, *args, **kwargs):
        """
            Место для реализации "бизнесс-логики" view.
            В методе нужно использовать функции "добавления" результата.
            По выходу из нее, "накопленный" результат будет выдан в JSON

            Определяется в потомках
        """

    def init_answer(self):
        """
            Инициализирует атрибуты для формирования "результата"
            По умолчанию устанавливает 'answer' = "success" с пустыми данными
        """
        self._answer = {self.ANSWER_ANSWER_KEY: self.ANSWER_SUCCESS_VAL}

    def set_answer_key(self, key, val):
        """
            Добваляет в накопленный ответ знчение в ключ key
        """
        self._answer[key] = val

    def get_answer_key(self, key, *args, **kwargs):
        """
            Возвращает значение ключа накопленного ответа.
            Если указан 3ий параметр или 'default' - то в случае отсутствия ключа
            будет возвращен он, а не исключение.
        """
        if args or 'default' in kwargs:
            if args:
                default = args[0]
            else:
                default = kwargs['default']
            return self._answer.get(key, default)
        else:
            self._answer[key]

    def append_answer_key(self, val_dict):
        """
            Добваляет в накопленный ответ словарь val_dict
        """
        self._answer.update(val_dict)

    def set_answer_success(self):
        """
        """
        self._answer[self.ANSWER_ANSWER_KEY] = self.ANSWER_SUCCESS_VAL

    def set_answer_error(self, err_msg, do_raise=True, do_clear=True):
        """
            Устанавливает статус ошибки и текст ошибки в err_msg.
            Если do_clear - то удаляет из ответа все другие данные.
            Если do_raise, то после установки данных в ответ будет вызвано исключение
                EJSONMixinErrorException.
                Это исключение может быть "отловлено" автоматически в обработке
        """
        if do_clear:
            self._answer = {}            
        self._answer[self.ANSWER_ANSWER_KEY] = self.ANSWER_ERROR_VAL
        self._answer[self.ANSWER_ERROR_KEY] = err_msg
        if do_raise:
            raise EJSONMixinErrorException(err_msg)    

    def get_answer(self):
        """
            Возвращает "накопленный" ответ в виде словаря
        """
        return self._answer

    def clean_input_params(self, request, *args, **kwargs):
        """
            Проверяет корректность входящих параметров с помощью формы класса <form_class>.
            В случае ошибки устанавливает errors и вызывает исключение. 
        """
        self.cleaned_params = {}
        self.input_errors = None
        if not self.PARAMS_FORM_CLASS:
            return

        form = self.PARAMS_FORM_CLASS(self.request_params)
        if not form.is_valid():
            if self.CLEAN_RAISE_ERROR:
                err_mes = self.compose_validate_error(form.errors)
                self.set_answer_error(err_mes, do_clear=False)
            else:
                self.input_errors = form.errors
                return
        self.cleaned_params = JSDict(form.cleaned_data.iteritems())

    def compose_validate_error(self, errors):
        """
            Возвращает скомпанованое сообщение об ошибке валидации входных 
            параметров.
            Может заполнить дополнительные ключи ответа.
            errors - объект errors формы.
        """
        self.set_answer_key("input_errors", errors)
        err_mes = u",".join(errors.keys())
        return u"Некорректные входные параметры: ({}).".format(err_mes)

    def get_output_data(self, request, *args, **kwargs):
        """
            Реализует процесс формирования данных.
            Для этого миксина - уже не переопределяется. Логика - в `process`
        """
        self.init_answer()

        cont = True
        try:
            self.clean_input_params(request, *args, **kwargs)
        except EJSONMixinErrorException as e:
            cont = False

        if cont:
            try:
                self.process(request, *args, **kwargs)
            except EJSONMixinErrorException as e:
                pass

        return self.get_answer()


class FilePostMixin(PostViewMixin, View):
    """
      Реализует метод post, возвращающий содержимое файла или файлового потока.

      Использование:
        class MyView(FilePostMixin, View)
        Определить get_output_data
        Уточнить CONTENT_TYPE и определить get_filename

      get_filename вызывается после формирования данных файла.
    """

    CONTENT_TYPE = 'application/vnd.ms-excel'
    DEF_FILE_NAME = 'my_file.xlsx'

    def get_output_data(self, request, *args, **kwargs):
        """
            Метод виртуальный. Переопределяется в потомках.
            Ожидает, что возвращает объект - файл
        """
        return None

    def get_file_contenttype(self, request, *args, **kwargs):
        """
            Возвращает строку - тип содержимого.
            По умолчанию возвращает константу self.CONTENT_TYPE
        """
        return self.CONTENT_TYPE

    def get_filename(self, request, *args, **kwargs):
        """
            Возвращает строку - название получаемого файла.
            По умолчанию возвращает константу self.DEF_FILE_NAME
        """

        return self.DEF_FILE_NAME

    def prepare_response(self, out_data, request, *args, **kwargs):
        """
           
        """
        ct = self.get_file_contenttype(request, *args, **kwargs)
        fn = self.get_filename(request, *args, **kwargs)
        response = HttpResponse(out_data, content_type=ct)
        response['Content-Disposition'] = 'attachment; filename="%s"' % (fn,)
        return response

