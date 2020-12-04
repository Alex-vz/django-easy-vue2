# -*- coding: utf-8 -*-

"""
    Extra For field:

    JSONField
"""

import json

from django.forms import Field, ValidationError


class JSONField(Field):
    """
        Принимает на вход строку с JSON. Преобразует ее в объект.
    """

    def to_python(self, value):
        """
        Validates that the input is a decimal number. Returns a Decimal
        instance. Returns None for empty values. Ensures that there are no more
        than max_digits in the number, and no more than decimal_places digits
        after the decimal point.
        """
        #django.core.serializers.json.DjangoJSONEncoder

        if value in self.empty_values:
            return None

        try:
            return json.loads(value)
        except Exception as e:
            raise ValidationError(repr(e), code='invalid')
