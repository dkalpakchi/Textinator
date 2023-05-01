# -*- coding: utf-8 -*-
from django.apps import AppConfig


class StringCombinatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'toolbox.string_combinator'
    label = 'toolbox_string_combinator'
    verbose_name = 'String Combinator (Toolbox)'
    verbose_short_name = 'String Combinator'
    description = 'A tool to easily design string transformations, save them into the transformation bank and then apply them to newly given strings.'
