# -*- coding: utf-8 -*-
from django.apps import AppConfig
from .string_combinator.apps import StringCombinatorConfig


TOOLS = [StringCombinatorConfig]

class ToolboxConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'toolbox'
