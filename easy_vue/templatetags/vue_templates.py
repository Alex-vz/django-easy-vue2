# -*- coding: utf-8 -*-
import datetime

import six
from django.conf import settings
from django import template
from django.utils.encoding import iri_to_uri
from django.utils.six.moves.urllib.parse import urljoin

register = template.Library()

@register.tag
def xtemplate(parser, token):
    """
    Вставляет определение шаблона vue x-template вида:
    <script type="text/x-template" id=":id:">
    :content:
    </script>
    :content: - все, что содержится между тегами {%xtemplate%} {%endxtemplate%}
    Внтури шаблонизатор django не действует, context недоступен.

    Использование::

        {% xtemplate template-id %}
            {{vue_data_atribute}}
        {% endxtemplate %}

    """
    # token.split_contents() isn't useful here because this tag doesn't accept variable as arguments
    TOKEN_TEXT = 0
    TOKEN_VAR = 1
    TOKEN_BLOCK = 2
    TOKEN_COMMENT = 3

    #args = token.contents.split()
    args = token.split_contents()
    if len(args) < 2:
        raise template.TemplateSyntaxError("'xtemplate' tag requires one or two arguments.")
    arg = args[1]

    res = ""
    endtag = 'endxtemplate'
    while parser.tokens:
        token = parser.next_token()
        if token.token_type == TOKEN_TEXT:
            res += token.contents
        elif token.token_type == TOKEN_VAR:
            res += ("{{"+token.contents+"}}")
        elif token.token_type == TOKEN_BLOCK and token.contents == endtag:
            break

    #nodelist = parser.parse(('endxtemplate',))
    #parser.delete_first_token()
    return XTemplateNode(res, arg)
    #return XTemplateNode(nodelist.render(template.Context()), arg)

@register.tag('vstatic')
def do_static(parser, token):
    """
    Joins the given path with the STATIC_URL setting.
    from 2 variants, according to VUE_DEBUG setting.
    1st - on True, 2nd on False.

    If present just 1 variant - it works just similar as 'static' 

    Usage::

        {% static path [path 2] [as varname] %}

    Examples::

        {% vstatic "myapp/css/base.css" "myapp/css/base.min.css" %}
        {% vstatic variable_with_path %}
        {% vstatic "myapp/css/base.css" as admin_base_css %}
        {% vstatic "myapp/css/base.css" "myapp/css/base.min.css" as admin_base_css %}
        {% vstatic variable_with_path as varname %}
    """
    return VueStaticNode.handle_token(parser, token)

@register.tag
def include_libs(parser, token):
    """
        Формирует теги SCRIPT и STYLE, подключая в них заданные библиотеки.
        Список нужных библиотек передается в виде списка ключей в параметре тега шаблона.
        Соотвествующие файлы библиотек задаются в settings.VUE_LIBRARIES

        Цель - обеспечить единообразное и короткое включение библиотек в шаблоны, 
        причем одинаковых версий с переключением dev | prod варианта.

        dev | prod выбирается в зависимости от значения settingt.VUE_DEBUG.
            True - dev вариант, False или не задано - production

        Формат settings.VUE_LIBRARIES:

            VUE_LIBRARIES = {
                "<key>": "<файл>",  # один файл и для разработки, и для production
                "<key>": ("<файл_dev>","<файл_prod>",),
                "<key>": {
                    "type": "<тип>",  # тип "js" для SCRIPT и "css" для STYLE
                    "dev": "<файл_dev>",     # Может быть указан только один файл
                    "prod": "<файл_prod>",
                    },  
                }

                файл указывается в формате для передачи в static()
                если "type" не задан явно, тип HTML тега определяется по крайнему расширению файла

        Usage::

            {% include_libs <dest> <key_1> <key_2> ... %}
            {% include_libs <dest> from <variable> %}

            <dest>: head или body

        Examples::

            {% include_libs bootstrap bootstrap_css vue vuex %}
            {% include_libs from my_libs %}
            my_libs - переменная контекста, содержащая список строк - ключей.

            VUE_LIBRARIES = {
                "vue": ("/common/vue.js", "/common/vue.min.js",), 
                "bootstrap_css": "/common/bootstrap.min.css",
                ...
                } 

    """
    return IncludeLibsNode.handle_token(parser, token)


#=====

class XTemplateNode(template.Node):
    def __init__(self, content, temp_id):
        self.content = content
        self.temp_id=temp_id

    def render(self, context):
        st1 = """<script type="text/x-template" id="{:s}">""".format(self.temp_id)
        st2 = """</script>"""
        #print st1+self.content+st2
        return st1+self.content+st2


class VueStaticNode(template.Node):
    def __init__(self, varname=None, path=None):
        if path is None:
            raise template.TemplateSyntaxError(
                "Static template nodes must be given a path to return.")
        self.path = path
        self.varname = varname

    def url(self, context):
        path = self.path.resolve(context)
        return self.handle_simple(path)

    def render(self, context):
        url = self.url(context)
        if self.varname is None:
            return url
        context[self.varname] = url
        return ''

    @classmethod
    def handle_simple(cls, path):
        try:
            from django.conf import settings
        except ImportError:
            prefix = ''
        else:
            prefix = iri_to_uri(getattr(settings, "STATIC_URL", ''))
        return urljoin(prefix, path)

    @classmethod
    def handle_token(cls, parser, token):
        """
        Class method to parse prefix node and return a Node.
        """
        bits = token.split_contents()

        if len(bits) < 2:
            raise template.TemplateSyntaxError(
                "'{}' takes at least one argument (path to file)".format(bits[0]))

        pb1 = bits[1]
        pb2 = None

        if len(bits) >= 2 and bits[-2] == 'as':
            varname = bits[-1]
            if len(bits)>4:
                pb2 = bits[2]
        else:
            varname = None
            if len(bits)>2:
                pb2 = bits[2]
        try:
            from django.conf import settings
        except ImportError:
            vd = False
        else:
            vd = getattr(settings, "VUE_DEBUG", False)

        if not vd and pb2:
            path = parser.compile_filter(pb2)
        else:
            path = parser.compile_filter(pb1)

        return cls(varname, path)


class IncludeLibsNode(template.Node):

    @classmethod
    def handle_token(cls, parser, token):
        """
        """
        bits = token.split_contents()
        if bits[1] == "from":
            #lkeys = parser.compile_filter(bits[2])
            return cls(keys_var=bits[2])
        else:
            return cls(keys_list=bits[1:])

    def __init__(self, keys_list=None, keys_var=None):
        """
            libs_keys - список строк - ключей подключаемых библиотек из переметра
            settings.VUE_LIBRARIES
            keys_list=None - список строк - ключей, 
            keys_var=None - название переменной контекста со списком ключей
            Должно быть указано что-то одно.
        """
        if not keys_list and not keys_var:
            raise Exception("No keys list present.")

        self.keys_list = keys_list
        self.keys_var = keys_var

    def resolve_static(self, path):
        prefix = iri_to_uri(getattr(settings, "STATIC_URL", ''))
        return urljoin(prefix, path)

    def resolve_filename(self, fname):
        if fname.startswith("https://") or fname.startswith("https://"):
            return fname
        return self.resolve_static(fname)

    def render_line(self, fkey, file_dev, file_prod, tag = None):
        """
        """
        if self.vue_debug:
            inc_file = self.resolve_filename(file_dev)
        else:
            inc_file = self.resolve_filename(file_prod)

        if tag is None:
            fff, dd, tag = inc_file.rpartition(".")

        if tag=="js" or tag=="JS":
            return '<SCRIPT SRC="{}"></SCRIPT>'.format(inc_file)
        elif tag=="css" or tag=="CSS":
            return '<LINK href="{}" rel="stylesheet">'.format(inc_file)
        else:
            raise Exception("Unknown file format for key '{}}'".format(fkey))

    def render_line_dict(self, fkey, file_dict):
        """
        """

    def render(self, context):
        conf = getattr(settings, "VUE_LIBRARIES")
        self.vue_debug = getattr(settings, "VUE_DEBUG", False)

        if not self.keys_list:
            try:
                self.keys_list = context[self.keys_var]
            except Exception as e:
                raise Exception("No keys list.")

        res = []

        for itm in self.keys_list:
            try:
                lib = conf[itm]
            except KeyError as e:
                raise Exception("Unknown library key '{}'".format(itm))

            if isinstance(lib, dict):
                res.append(self.render_line_dict(itm, lib))
                continue
            elif isinstance(lib, six.string_types):
                res.append(self.render_line(itm, lib, lib))
                continue

            try:
                f1 = lib[0]
            except Exception as e:
                raise Exception("Unknown library format for key '{}'".format(itm))

            try:
                f2 = lib[1]
            except Exception as e:
                f2 = f1
            res.append(self.render_line(itm, f1, f2))

        return "\n".join(res)
