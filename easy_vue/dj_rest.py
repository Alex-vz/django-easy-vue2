# -*- coding: utf-8 -*-

# @Date    : 2017-02-21 09:51:10
# @Author  : Your Name (you@example.org)
# @Link    : http://example.org
# @Version : $Id$

"""
    RESTful easy Django extension.

    View than support any HTTP methods and returs JSON with any status
"""

from __future__ import unicode_literals

import six
import json

from .lib import JSDict

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import (Http404, JsonResponse, FileResponse, HttpResponse, 
    HttpResponseRedirect, HttpResponseForbidden)
from django.views.generic.base import ContextMixin, TemplateView, View
from django.utils.encoding import iri_to_uri
from django.utils.six.moves.urllib.parse import urljoin

from . import dj_rest_params


class ViewAccessParams(object):
    """
        Служебный класс, экземпляр его передается в настройки прав доступа в RESTView.
        При создании объекта указываются значения тех параметров, которые нужно переопределить.
            ajax_only=False
            registered_only=False
            active_only=True
            permissions = None
    """

    def __init__(self, **kwargs):
        """
        """
        self.ajax_only = kwargs.get("ajax_only", False)
        self.registered_only = kwargs.get("registered_only", False)
        self.active_only = kwargs.get("active_only", True)
        self.permissions = kwargs.get("ajax_only", None)


class UseAccessParams(ViewAccessParams):
    """
        Служебный класс, индицирующий, что параметры доступа нужно взять из
        определения другого, указанного метода, имя которого передается в init
    """

    def __init__(self, method):
        """

        """
        super(UseViewAccessParams, self).__init__()
        self.use_method = method

    def load(self, access_defs):
        try:
            src = access_defs[self._method]
        except KeyError as e:
            raise Exception("Unknown method for ViewAccessParams: ''".format(self._method))
        self.ajax_only = src.ajax_only
        self.registered_only = src.registered_only
        self.active_only = src.active_only
        self.permissions = src.ajax_only


class EResponseForbidden(Exception):
    """
        Сигнализирует, что выявлен недопуск пользователя
    """


class EResponseDataError(Exception):
    """
        Сигнализирует, что выявлен некооректность в данных
    """


class RESTView(View):
    """
      Реализует метод post к обычному View, обеспечивая возврат ответа в виде JSON,
      возможно со статусом, отличным от 200.

        Так же проверяет условия доступа к ресурсу, аутентификацию, запрос по AJAX,
        наличие csrf.

        Устанавливает режим ответа в случае ошибки:

        DATA_ERROR_BY_STATUS (= True) - Будет ответ со статусом: DATA_ERROR_STATUS
        USER_ERROR_BY_STATUS (= True)  - Будет ответ со статусом: FORBIDDEN_STATUS
        Если False, то статус ответа - 200, но в JSON ответа будет установлен ключ
            ANSWER_KEY в значение ERROR_WORD,
            а ключи ERROR_MESSAGE_KEY и ERROR_CODE_KEY соотвественно, текст ошибки и код
            В этом режиме если нет ошибки - ANSWER_KEY в значение SUCCESS_WORD.
            В режиме статуса ключ ANSWER_KEY автоматически не проставляется.

        Для проверки входящих параметров / данных можно использовать форму.
            PARAMS_FORM_CLASS - класс формы для проверки.
            CLEAN_RAISE_ERROR - если True, то в случае ошибки формы будет автоматически сформирован ответ с
                ошибкой, иначе - продолжится работа, ошибки вализации нужно будет
            Определяет атрибуты:
                cleaned_params::JSDict - "преобразованные" атрибуты запроса
                input_errors -- объект form.errors
                input_form::Form -- инициализированный объект формы

            Вместо PARAMS_FORM_CLASS можно определить списки параметров в атрибутах:
                COMMON_IN_PARAMS, POST_IN_PARAMS, GET_IN_PARAMS.
                Это списки экземпляров классов от dj_rest_params.IncomingParamBase
                Сначала разбираются параметры из списка COMMON_IN_PARAMS, а потом - POST_IN_PARAMS или 
                GET_IN_PARAMS или аналогичный в зависимости от метода запроса.
                
                Результат в 
                cleaned_params::JSDict - "преобразованные" атрибуты запроса
                input_errors -- Список текстов ошибок разбора, если CLEAN_RAISE_ERROR==False

        Для формирования результата вызывается метод process_<request.method>,
        а если такового нет - то просто process

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
            ensure_csrf - гарантирует наличие заголовка csrf

            permissions - список названий разрешений, требуемых у пользователя для доступа.
                Все перечисленные разрешения должны присутствовать одновременно.
                Для проверки вызывает check_user_permissions, который может быть переопределен.
                Работает только с registered_only=True.
                Если permissions is None - разрешения не проверяются.

        Использование:
            class MyView(RESTView)

        Для реализации бизнеслогики можно определить методы process_get, process_post,... для
            всех нужных вариантов. Если конкретного варианта нет - будет вызван метод process.
            Сигнатура вызова всех методов одинакова с process
    """

    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options', ]
    #http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace']

    ensure_csrf = False
    ajax_only=False
    registered_only=False
    active_only=True
    permissions = None

    PARAMS_FORM_CLASS = None
    CLEAN_RAISE_ERROR = True

    DATA_ERROR_BY_STATUS = True
    USER_ERROR_BY_STATUS = True

    ERROR_MESSAGE_KEY = "error"
    ERROR_CODE_KEY = "error_code"
    ANSWER_KEY = "answer"
    SUCCESS_WORD = "success"
    ERROR_WORD = "error"
    USER_FORBIDDEN_MESSAGE = u"Доступ запрещен"

    DATA_ERROR_STATUS = (422, "Unprocessable Entity")
    FORBIDDEN_STATUS = (403, "Forbidden")
    #FORBIDDEN_STATUS = (404, "Not Found")
    NOT_ALLOWED_STATUS = (405, "Method Not Allowed")
    EXCEPTION_STATUS = (500, "Internal Server Error")
    UNACCEPTABLE_STATUS = (501, "Not Implemented")

    DATA_POST_METHODS = ('POST', 'PUT', 'PATCH',)
    DATA_GET_METHODS = ('GET', 'HEAD', 'PATCH', 'OPTIONS',)

    def process(self, request, *args, **kwargs):
        """
            Место для реализации "бизнесс-логики" view.
            В методе нужно использовать функции "добавления" результата.
            По выходу из нее, "накопленный" результат будет выдан в JSON

            Для добавления данных в ответ можно использовать:
            set_answer_key(key, val)

            set_answer_error(err_msg, do_raise=True, do_clear=True)
            set_user_error(err_msg, do_raise=True, do_clear=True)

            self.request_params
            Определяется в потомках
        """

    def allow_user_access(self, request, *args, **kwargs):
        """
            Дополнительно проверяет, разрешен ли доступ пользователя к текущему View.
            Может быть переопределен в потомках.
            Дефолтовая реализация использует настройки access_params.
        """
        if self.registered_only:
            if request.user.is_authenticated() and (request.user.is_active or not self.active_only):
                return self.check_user_permissions(request.user)
            else:
                return False
        else:
            return True

    def get_param_form(self, request, *args, **kwargs):
        """
            Возвращает форму для проверки входящих параметров.
            Можно переназначить в потомках
        """
        return self.PARAMS_FORM_CLASS

    # ====

    @classmethod
    def as_view(cls, **initkwargs):
        view = super(RESTView, cls).as_view(**initkwargs)
        if cls.ensure_csrf:
            return ensure_csrf_cookie(view)
        else:
            return view

    def set_answer_success(self):
        """
            Добавляет в ответ ключ "answer":"success"
        """
        self.set_answer_key(self.ANSWER_KEY, self.SUCCESS_WORD)

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

    def set_answer_error(self, err_msg, err_code=None, do_clear=True, data=None, _except_class=None, do_raise=True):
        """
            Устанавливает статус ошибки и прерывает процесс сбора результата.
            err_msg - текст ошибки, Unicode. Устанавливается в ключ error_message 
            err_code - код ошибки
            data - дополнительные данные, которые будут переданы с ответом.

            Если do_clear=False, то ключи ошибки и data добавляются к накопленному ответу.
            Если do_clear - то удаляет из ответа все другие данные.

            _except_class - служебный параметр
        """

        if do_clear:
            self._answer = {}

        self._answer[self.ERROR_MESSAGE_KEY] = err_msg
        if err_code is not None:
            self._answer[self.ERROR_CODE_KEY] = err_code

        self._answer[self.ANSWER_KEY] = self.ERROR_WORD

        if do_raise:
            if _except_class is not None:
                raise _except_class()    
            else:
                raise EResponseDataError()    

    def set_user_error(self, err_msg=None, err_code=None, do_clear=True, data=None, do_raise=True):
        """
            Устанавливает статус ошибки связанный с пользователем прерывает процесс сбора результата.
            err_msg - текст ошибки, Unicode. Если не задан - то используется USER_FORBIDDEN_MESSAGE.
            err_code - код ошибки
            data - дополнительные данные, которые будут переданы с ответом.

            Если do_clear=False, то ключи ошибки и data добавляются к накопленному ответу.
            Если do_clear - то удаляет из ответа все другие данные.
        """

        self.set_answer_error(err_msg if err_msg is not None else self.USER_FORBIDDEN_MESSAGE,
            err_code=err_code, do_clear=do_clear, data=data, 
            _except_class=EResponseForbidden, do_raise=do_raise)

    def set_form_error(self, err_code=None, do_clear=True, data=None, do_raise=True):
        """
            Устанавливает статус ошибки связанный с пользователем прерывает процесс сбора результата.
            err_msg - текст ошибки, Unicode. Если не задан - то используется USER_FORBIDDEN_MESSAGE.
            err_code - код ошибки
            data - дополнительные данные, которые будут переданы с ответом.

            Если do_clear=False, то ключи ошибки и data добавляются к накопленному ответу.
            Если do_clear - то удаляет из ответа все другие данные.
        """
        if do_clear:
            self.clear_answer()
        err_mes = self.compose_validate_error(self.input_form.errors)
        self.set_answer_error(err_mes, err_code=err_code, data=data, do_clear=False, 
            do_raise=do_raise, _except_class=EResponseDataError)

    def clear_answer(self):
        """
            Очищает накопленный ответ
        """
        self._answer = {}

    def get_answer(self):
        """
            Возвращает "накопленный" ответ в виде словаря
        """
        return self._answer

    # ====

    def clean_input_params(self, request, *args, **kwargs):
        """
            Проверяет корректность входящих параметров с помощью формы класса <form_class>.
            В случае ошибки устанавливает errors и вызывает исключение. 

            Определяет атрибуты:
                cleaned_params::JSDict - "преобразованные" атрибуты запроса
                input_errors -- объект form.errors
                input_form::Form -- инициализированный объект формы

        """
        self.cleaned_params = {}
        self.input_errors = None
        Form = self.get_param_form(request, *args, **kwargs)

        if Form:
            self.clean_by_form(Form, request, *args, **kwargs)
        else:
            self.clean_by_params(request, *args, **kwargs)

    def clean_by_params(self, request, *args, **kwargs):
        """
        """
        self.input_errors = []

        common_params = getattr(self, "COMMON_PARAMS", None)
        if common_params:
            self.parse_in_params(common_params,self.request_params)

        det_params = getattr(self, "{}_PARAMS".format(request.method), None)
        if det_params:
            self.parse_in_params(det_params,self.request_params)

        self.cleaned_params = JSDict(self.cleaned_params.iteritems())

        if not self.input_errors:
            self.input_errors = None

    def parse_in_params(self, params_list, request_dict):
        """
            Выполняет разбор параметров по списку params_list.
            request_dict -- список входящих параметров с запроса
        """

        for itm in params_list:
            err = ""
            try:
                itm.parse(request_dict, self.cleaned_params)
            except dj_rest_params.EParseError as e:
                err = e.u_msg
            except Exception as e:
                err = str(e)
            if err:
                if self.CLEAN_RAISE_ERROR:
                    self.set_answer_error(err, do_clear=False)
                else:
                    self.input_errors.append(err)

    def clean_by_form(self, Form, request, *args, **kwargs):
        """
        """
        self.input_form = None
        form = Form(self.request_params)
        self.input_form = form 
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

    def dispatch(self, request, *args, **kwargs):
        """
            Проверяет допустимость метода, AJAX, пользователя и т.п.
        """

        if not ((request.method.lower() in self.http_method_names) and ((self.ajax_only and self.request.is_ajax()) or not self.ajax_only)):
            return self.http_method_not_allowed(request, *args, **kwargs)

        if not self.allow_user_access(request, *args, **kwargs):
            self.set_user_error(do_raise=False)
            return self.create_responce(self.USER_ERROR_BY_STATUS,
                data=self.get_answer(),
                status=self.FORBIDDEN_STATUS)

        if request.method in self.DATA_POST_METHODS:
            self.request_params = request.POST
        elif request.method in self.DATA_GET_METHODS:
            self.request_params = request.GET
        else:
            self.request_params = None

        self.init_answer()
        try:
            self.clean_input_params(request, *args, **kwargs)
            process = getattr(self, "process_"+request.method.lower(), self.process)
            process(request, *args, **kwargs)
        except EResponseForbidden as e:
            return self.create_responce(self.USER_ERROR_BY_STATUS,
                data=self.get_answer(),
                status=self.FORBIDDEN_STATUS)
        except EResponseDataError as e:
            return self.create_responce(self.DATA_ERROR_BY_STATUS,
                data=self.get_answer(), 
                status=self.DATA_ERROR_STATUS)
        except Exception as e:
            raise

        return self.create_responce(data=self.get_answer())

    def http_method_not_allowed(self, request, *args, **kwargs):
        return self.create_responce(True, data={}, 
            status=self.NOT_ALLOWED_STATUS, 
            heads={'Allow':self.http_method_names})

    def create_responce(self, by_status=True, data=None, status=None, heads=None):
        """
            by_status если False, то статус 200, иначе status
            status: (<код>, <текст>). Если не указан - то 200
            data:   dict. Если не указан - формируется обычный ответ, а не JSON
            heads - значения заголовков
        """
        if data is None:
            response = HttpResponse()
        else:
            response = JsonResponse(data)

        if heads:
            for itm in heads:
                response[itm] = heads[itm]
        if by_status and status:
            response.status_code = status[0]
            response.reason_phrase = status[1]

        return response

    def _need_answer_key(self):
        return not (self.DATA_ERROR_BY_STATUS and self.USER_ERROR_BY_STATUS)

    def init_answer(self):
        """
            Инициализирует атрибуты для формирования "результата"
            По умолчанию устанавливает 'answer' = "success" с пустыми данными
        """
        self._answer = {}
        if self._need_answer_key():
            self._answer[self.ANSWER_KEY] = self.SUCCESS_WORD

    # ====

    def get_active_access_params(self, method):
        """
            Вычисляет объект класса ViewAccessParams, соотвествующий переданному методу.
        """
        if not self.access_params:
            return ViewAccessParams()

        viewed = set()
        chk = [method]

        cm = method
        while True:
            if cm in viewed:
                raise Exception("Circular reference in 'access_params' method '{}'".format(cm))
            ap = self.access_params.get(cm)
            viewed.add(cm)
            if ap is not None:
                if isinstance(ap, UseAccessParams):
                    cm = ap.use_method
                    continue
                elif isinstance(ap, ViewAccessParams):
                    return ap
                else:
                    raise Exception("Uncorrect 'access_params' item for '{}'".format(cm))
            else:
                break

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


def get_from_static(static_name):
    """
        Возвращает полный путь относительно корня статики, как {%static%}
    """
    prefix = iri_to_uri(getattr(settings, "STATIC_URL", ''))
    return urljoin(prefix, static_name)


def get_from_vue(file_id):
    """
        Возвращает полный путь относительно корня сайта файла, указаного в 
        VUE_LIBRARIES, с учетом VUE_DEBUG.
        Возвращает словарь с полями: type, filename
    """
    vue_debug = getattr(settings, "VUE_DEBUG", settings.DEBUG)
    file_def = settings.VUE_LIBRARIES[file_id]

    if isinstance(file_def, six.string_types):
        filename = file_def
    else:
        try:
            if vue_debug:
                filename = file_def[0]
            else:
                filename = file_def[1]
        except Exception as e:
            raise Exception("Uncorrect VUE_LIBRARIES settings for '{}'.".format(file_id))

    fff, dd, tag = filename.rpartition(".")
    if not tag:
        tag = "js"
    else:
        tag = tag.lower()

    if filename.startswith("https://") or filename.startswith("https://"):
        pass
    else:
        filename = get_from_static(filename)
    return dict(type=tag, filename=filename)


def get_from_wp(app, filename):
    """
        Возвращает словарь с полями: type, filename,
        filename будет содержать полный путь с корня сайта плюс хеш сборки.
        Входящие app, filename идентифицируют файл в соответствии с настройками модульной сборки.
    """
    if not _WP_HASHES:
        _generate_wp_descr(_WP_HASHES)

    descr = _WP_HASHES.get("{}.{}".format(app, filename))
    if descr is None:
        raise Exception("Unknown bundled script for {}.{}".format(app, filename))
    fpath = descr.get("path")
    if fpath is None:
        raise Exception("Unknown path for bundled script for {}.{}".format(app, filename))
    hsh = descr.get("hash")
    if not hsh:
        hsh = "1"
    return dict(type="js", filename="{}?h={}".format(get_from_static(fpath), hsh))


def with_version(filename, vnum=None, vkey=None):
    """
        Добавляет к имени файла filename номер "версии".
        Значение берет или переданное в vnum или из специальной таблицы версий по ключу vkey
    """
    return "{}?{}".format(filename, vnum)


ScriptLine = JSDict.custom_class(b"ScriptLine", 
    """
        type: "css" | "js"
        filename, 
            - полный URL, начинающийся с http или https
            - Относительный url, начинающийся с "/"
            Для заполнения имен можно использовать функции:
                get_from_static, get_from_vue, with_version
        text
            - Текст скрипта или css. Если указан filename, то используется он.
    """,
    ["type", "filename", "text"])


class VueBaseView(TemplateView):
    """
        View, формирующее страницу с помощью Vue.js или аналогичных фреймверков.
        Автоматизированно подгружает скрипты, контекст и прочее.
        Используется шаблон "специального" вида или унаследованный от него.

        Для контроля доступа пользователей можно применять типовые:
            LoginRequiredMixin
            PermissionRequiredMixin
            UserPassesTestMixin
    """

    template_name = "vjs_base.html"
    vue_use = ["Vuex", "Router"]
    page_title = "Vue page"
    vue_element_id = "app"

    SCRIPT_TYPES = ["css", "js"]
    ScriptLine = ScriptLine

    def get_head_scripts(self):
        """
            Возвращает список объектов ScriptLine, из которых будет сформированы скрипты
            в заголовке
        """
        return []

    def get_body_scripts(self):
        """
            Возвращает список объектов ScriptLine, из которых будет сформированы скрипты
            в конце body документа
        """
        return []

    def get_start_scripts(self):
        """
            Возвращает список объектов ScriptLine, из которых будет сформированы скрипты
            после body_script, инициализирующие данные.
        """
        return []

    def get_window_context(self):
        """
            Возвращает словарь. Ключи - глобальные переменные в window, значения - в значения.
            Передается на страницу через JSON, по этому должет быть JSON сериализуем.
        """
        return {}

    def init_process(self):
        """
            Дополнительная инициалиазция перед формированием контекста.
            self.context уже сформирован
        """

    def process(self):
        """
            Дополнительное заполнение данными self.context
            self.context уже заполнен всеми другими данными
            window_context находится еще в виде словаря
            Определяется в потомках
        """

    def get_page_title(self):
        """
            Возвращает параметр для заголовка страницы.
        """
        return self.page_title

    def get_vue_element_id(self):
        """
            Возвращает ID элемента, в который будет встраиваться Vue 
        """
        return self.vue_element_id

    def get_vue_use(self):
        return self.vue_use

    def append_static_css(self, lst, static_name):
        """
            helper функция
        """
        lst.append(self.ScriptLine(type="css", filename = get_from_static(static_name)))

    def append_static_js(self, lst, static_name):
        """
            helper функция
        """
        lst.append(self.ScriptLine(type="js", filename = get_from_static(static_name)))

    def append_script(self, lst, text):
        """
            helper функция. Добавляет текст скрипта
        """
        lst.append(self.ScriptLine(type="js", text=text))

    def append_vues(self, lst, vues_list):
        """
            helper функция
        """
        for itm in vues_list:
            lst.append(self.ScriptLine(**get_from_vue(itm)))

    def append_bundled(self, lst, app, fname):
        """
            helper функция
        """
        lst.append(self.ScriptLine(**get_from_wp(app, fname)))

    #====
    def get_context_data(self, **kwargs):
        self.context = super(VueBaseView, self).get_context_data(**kwargs)
        self.init_process()
        self.context["page_title"] = self.get_page_title()
        self.context["vue_element_id"] = self.get_vue_element_id()
        self.context["head_scripts"] = self.get_head_scripts()
        self.context["body_scripts"] = self.get_body_scripts()
        self.context["window_context"] = self.get_window_context()
        self.context["vue_use"] = self.get_vue_use()
        self.context["start_scripts"] = self.get_start_scripts()
        self.process()

        if self.context["window_context"] is not None:
            self.context["window_context"] = json.dumps(self.context["window_context"])
        else:
            self.context["window_context"] = None

        return self.context



#===========
def _generate_wp_descr(res):
    """
        Читает файл данных хешкодов сборки, сохраняет их в глобальную переменную модуля
        _WP_HASHES

        _WP_HASHES: {<app.filename>:{static_name, hash}}
    """
    #HASHES_FILENAME = "chunkdata.json"

    buf = "["
    d=""
    with open(settings.HASHES_FILENAME, "r") as ff:
        for st in ff:
            buf += d + st
            d=","
    buf += "]"
    data = json.loads(buf)

    #res = {}
    if not hasattr(data, "__iter__"):
        print "Uncorrect {}".format(settings.HASHES_FILENAME)
        return res
    for itm in data:
        try:
            res[itm["chunk_name"]] = dict(path=itm["path"], hash=itm["hash"])
        except KeyError as e:
            pass


_WP_HASHES = {}