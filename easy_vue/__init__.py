# -*- coding: utf-8 -*-
from __future__ import unicode_literals

"""
  Утилиты для работы с Vue и другими JavaScript фреймверками.
"""

from django.apps import AppConfig

class EasyVueConfig(AppConfig):
    name = 'easy_vue'
    verbose_name = "EasyVue"

default_app_config = "easy_vue.EasyVueConfig"