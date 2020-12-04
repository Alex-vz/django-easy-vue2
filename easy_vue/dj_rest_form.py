# -*- coding: utf-8 -*-

"""
	REST расширение для Form и ModelForm.

	Выдает для выгрузки в JSON:
		to_dict -- данные формы + ошибки
		get_choices_for -- список подстановок для поля с учетом текущего контекста
		metadata_dict -- словарь метаданных формы - названия, типы полей, параметры.

	RESTFormProcessor -- специальный класс, инициализируемый формой. Позволяет добавить функциональность без модификации самой формы.

	RESTFormMixin -- миксин для добавления в форму, как Form, так и ModelForm

	Для добавления кастомизации можно либо расширить класс формы, установив предварительно миксин,
	Или расширить класс RESTFormProcessor и использовать его.
"""

import json

from django.forms import Form, ModelForm, MultipleChoiceField, ChoiceField
from django.forms.models import ModelMultipleChoiceField, ModelChoiceField
from django.utils.translation import gettext as _


class RESTFormProcessor(object):
    """
        Реализует получение JSON данных для формы.
        Сделан отдельным объектом, что бы можно было использовать эту 
        функциональность для немодифицированных форм.
        Для собственных форм удобнее использовать mixin.
    """

    def __init__(self, form):
        """
        """
        self.form = form

    def to_dict(self, just_data=False):
        """
            Выгрузка формы в словарь для последующей отправки как JSON
            just_data=True -- выгрузка только данных, без сообщений об ошибках.
        """

        instance = getattr(self.form, "instance", None)
        if instance:
            res = {"pk": dict(type="pk", val=dict(value=instance.id))}
        else:
            res = {"pk": dict(type="pk", val=None)}

        top_errors = self.form.non_field_errors()
        errs = {}
        if top_errors:
            errs["__nonfiled__"] = [st for st in top_errors]

        for name, field in self.form.fields.items():
            has_choices = hasattr(field, "choices")
            has_options = hasattr(field.widget, "options")
            is_model = isinstance(field, ModelChoiceField)
            bf = self.form[name]
            bf_errors = self.form.error_class(bf.errors)
            #if bf.is_hidden
            if bf.errors:
                errs[name] = [st for st in bf.errors]

            """
            subwidgets=[]
            for itm in bf.subwidgets:
                subwidgets.append(str(itm))
            """

            if hasattr(bf.field.widget, "format_value"):
                format_val=bf.field.widget.format_value(bf.value())
            else:
                format_val=unicode(bf.value())

            #gatherin choices values
            choices = []
            if False and has_choices:
                choices = field.choices

            attrs = self._get_bf_attrs(bf)
            wchoices=[]
            if False and has_options:
                wchoices = [(str(ii[0]), ii[1]) for ii in field.widget.choices]
                for itm in field.widget.options(bf.html_name, format_val, attrs):
                    dd = {}
                    for k, v in itm.items():
                        dd[k]=str(v)
                    choices.append(dd)

            widget_attrs={}
            for itm, val in field.widget.attrs.items():
                widget_attrs[itm] = str(val)

            if bf.value() is None:
                model_val = None
            else:
                if isinstance(field, ModelMultipleChoiceField):
                    model_val = None
                elif isinstance(field, ModelChoiceField):
                    model_val = self._get_model_val(bf, field, format_val, attrs)
                elif isinstance(field, ChoiceField):
                    model_val = self._get_choise_val(bf)
                    # model_val = self._get_model_val(bf, field, format_val, attrs)
                else:
                    model_val = dict(value=bf.value())

            res[name] = dict(
                type=self._field_classname(field),
                bf_val=bf.value(),
                val=model_val,
                #subwidgets=subwidgets,
                #widget_attrs=widget_attrs,
                has_choices=has_choices,
                choices=choices,
                #wchoices = wchoices,
                has_options=has_options,
                #attrs=attrs,
                html_name=bf.html_name,
                is_model=is_model,
                )

        if just_data:
            res1={}
            for fld, val in res.items():
                if val["val"] is not None:
                    res1[fld]=val["val"]["value"]
                else:
                    res1[fld]=None
            return res1
        else:
            return dict(errors=errs, data=res)

    def get_choices_for(self, field_name, context=None):
        """
            Возвращает список подстановок для указанного поля.
            Для моделей используется модифицированный QuerySet с помощью
            метода get_context_queryset 
        """
        bf = self.form[field_name]
        is_model = isinstance(bf.field, ModelChoiceField)
        has_choices = hasattr(bf.field, "choices")
        if not has_choices:
            return []

        if hasattr(bf.field.widget, "format_value"):
            format_val=bf.field.widget.format_value(bf.value())
        else:
            format_val=unicode(bf.value())

        if is_model:
            old_qs = bf.field.queryset
            new_qs = self._i_get_context_queryset(bf, context, old_qs)
            bf.field.queryset = new_qs

            attrs = self._get_bf_attrs(bf)
            choices = self._get_woptions(bf, bf.html_name, format_val, attrs)
            bf.field.queryset = old_qs
        else:
            choices = [dict(value=str(ii[0]), label=ii[1]) for ii in bf.field.widget.choices]

        return self._i_filter_choices(bf, choices, context)

    def metadata_dict(self):
        """
            Возвращает словарь метаданных формы.
        """
        fields = {}
        for name, field in self.form.fields.items():
            validators = []
            for itm in field.validators:
                validators.append(dict(
                    type=self._field_classname(itm),
                    attrs = self._get_obj_attrs(itm)
                    ))

            fields[name]=dict(name=name, type=self._field_classname(field),
                default_error_messages = field.default_error_messages,
                disabled=field.disabled,
                #empty_values=field.empty_values,
                error_messages=field.error_messages,
                help_text=field.help_text,
                initial=field.initial,
                label=field.label,
                label_suffix=field.label_suffix,
                localize=field.localize,
                #max_length=field.max_length,
                #min_length=field.min_length,
                required=field.required,
                validators=validators,
                widget=self._field_classname(field.widget),
                #widget_attrs=field.widget_attrs
                )
            fields[name].update(self._get_obj_attrs(field, self.FLD_ATTR_NAMES))

        return dict(fields=fields)

    def filter_choices(self, bf, choices, context):
        """
            Фильтрует список выбора исходя из контекста.
            возвращает новый список
        """
        return choices

    def get_context_queryset(self, bf, context, queryset):
        """
            Возвращает модифицированный queryset.
            изначальный вариант возвращает исходный queryset для указаного поля.
            Или None, если поле не относится к моделям.
        """
        return queryset

    def get_model_dict_for(self, bf, obj):
        """
            Возвращает словарь дополнитеьных значений из модели obj
            из списка choices для поля bf
            Добавляется в поле obj значения самого поля или выбора.
            Если возвращает None - поле obj не добавляется.
        """
        return None

    def _i_filter_choices(self, bf, choices, context):
        """
        """
        if hasattr(self.form, "filter_choices"):
            return self.form.filter_choices(bf, choices, context)
        else:
            return self.filter_choices(bf, choices, context)

    def _i_get_model_dict_for(self, bf, obj):
        """
            Возвращает словарь дополнитеьных значений из модели obj
            из списка choices для поля bf
            Добавляется в поле obj значения самого поля или выбора.
            Если возвращает None - поле obj не добавляется.
        """
        if hasattr(self.form, "get_model_dict_for"):
            return self.form.get_model_dict_for(bf, obj)
        else:
            return self.get_model_dict_for(bf, obj)

    def _get_bf_attrs(self, bf):
        """
        """
        id_ = bf.field.widget.attrs.get('id') or bf.auto_id
        if hasattr(bf, "build_widget_attrs"):
            return bf.build_widget_attrs({'id': id_} if id_ else {})
        elif hasattr(bf, "build_attrs"):
            return bf.build_attrs({'id': id_} if id_ else {})
        else:
            return {'id': id_} if id_ else {}

    def _i_get_context_queryset(self, bf, context, queryset):
        """
        """
        if hasattr(self.form, "get_context_queryset"):
            return self.form.get_context_queryset(bf, context, queryset)
        else:
            return self.get_context_queryset(bf, context, queryset)

    def _field_classname(self, fld):
        cls = str(fld.__class__).split("'")
        return cls[1]

    def _get_obj_attrs(self, obj, exclude=None):
        if exclude is None:
            exclude = []
        dd = {}
        for itm in dir(obj):
            if itm in exclude:
                continue
            if itm.startswith("_"):
                continue
            try:
                av = getattr(obj, itm)
            except Exception as e:
                continue

            #if isinstance(av, Callable):
            if callable(av):
                continue

            if itm=="choices":
                av = [(str(vv[0]), str(vv[1])) for vv in av]
            else:
                try:
                    vv = json.dumps(av)
                except Exception as e:
                    av = str(av)

            dd[itm] = av

        return dd

    def _get_woptions(self, bf, html_name, format_val, attrs):
        """
        """
        choices=[]
        if hasattr(bf.field.widget, "options"):
            for itm in bf.field.widget.options(html_name, format_val, attrs):
                if itm["value"] is None or itm["value"]=="":
                    continue
                obj_dict = self._i_get_model_dict_for(bf, itm["value"].instance)
                ch = dict(value=str(itm["value"]), label=itm["label"])
                if obj_dict is not None:
                    ch["obj"] = obj_dict
                choices.append(ch)
        else:
            obj_idx = {}
            for itm in bf.field.choices:
                if itm[0] is None or itm[0]=="":
                    continue
                ch = dict(value=unicode(itm[0]), label=itm[1])
                obj_idx[ch["value"]] = len(choices)
                choices.append(ch)

            for itm in bf.field.queryset:
                obj_dict = self._i_get_model_dict_for(bf, itm)
                if obj_dict is None:
                    continue
                ch = obj_idx.get(unicode(itm.pk))
                if ch is not None:
                    choices[ch]["obj"] = obj_dict

        return choices

    def _get_model_val(self, bf, field, format_val, attrs):
        """
            Возвращает словарь {id, text} значения, развернутого из ссылки
        """
        if bf.value() is None:
            return None

        chi = field.queryset
        field.queryset = field.queryset.filter(pk=bf.value())

        choices = self._get_woptions(bf, bf.html_name, format_val, attrs)
        field.queryset = chi

        if not choices:
            return None

        return choices[0]

    def _get_choise_val(self, bf):
        """
        """
        wchoices = [(str(ii[0]), ii[1]) for ii in bf.field.widget.choices]
        val = str(bf.value())
        for key, v in wchoices:
            if key==val:
                return dict(value=val, label=v)

        return None

    FLD_ATTR_NAMES=[
          "default_error_messages",
          "default_validators",
          "disabled",
          "empty_value",
          "empty_values",
          "error_messages",
          "help_text",
          "hidden_widget",
          "initial",
          "label",
          "label_suffix",
          "localize",
          #"max_length",
          #"min_length",
          "required",
          "validators",
          "widget",
          #"widget_attrs"
          #----
          "queryset",
    ]


class RESTFormMixin(Form):
    """
        Добавляет функциональность REST к форме


        Можно определить следующие методы в класссе:

        def filter_choices(self, bf, choices, context):
            '''
                Фильтрация списка подстановок с учетом context. Возвращает новый список.
                bf.name - имя поля
            '''
            return choices

        def get_context_queryset(self, bf, context, queryset):
            '''
                Модифицирует querysetс учетом context
            '''
            return queryset

        def get_model_dict_for(self, bf, obj):
            '''
                Формирует словарь с дополнительными данными от модели подстановки.
                Если возвращает None - то поле obj не будет добавляться в словарь выдачи.
            '''
            return None

    """

    RESTFormProcessorClass = RESTFormProcessor

    def to_dict(self, just_data=False):
        """
            Выгружает текущие данные формы и ошибки в словарь,
                годный для последующей отправки в JSON
            Если just_data=True, то выгружаются только непосредственно значения полей,
            иначе значения выгружаются в "расширенном" формате в виде словаря с
                обязательным полем value. А для полей с подстановкой указывается еще
                поле label, содержащее текст значения подстановки.
                а для моделей возможно еще и obj с дополнитлеьныеми значениями по связанному объекту.
        """
        proc = self.RESTFormProcessorClass(self)
        return proc.to_dict(just_data)

    def get_choices_for(self, field_name, context=None):
        """
            Получить список данных для подстановки в поле.
            В виде [{label, val, obj}]
            Данные могут формироваться и фильтроваться с учетом context.
                obj - необязательный компонент, формирующийся когда список создается из
                    модели. Позволяет передать дополнительные данные о вариантах выбора.
                    Определяется с помощью метода get_model_dict_for

            При формировании списка, для запроса из модели сначала используется
                метод get_context_queryset, модифицирующий исходный queryset поля с учетом
                переданного context.
            Потом полученный список фильтруюется с помощью метода filter_choices.
                Эта фильтраци яприменяется как для моделей, так и для статическойго списка.
        """
        proc = self.RESTFormProcessorClass(self)
        return proc.get_choices_for(field_name, context)

    def metadata_dict(self):
        """
            Формирует словарь содержащий метаданные формы, 
                годный для последующей отправки в JSON.
            Метаданные - список полей, типов, атрибутов настроек и прочего.
        """
        proc = self.RESTFormProcessorClass(self)
        return proc.metadata_dict()


