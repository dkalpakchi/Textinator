# -*- coding: utf-8 -*-
from django.contrib import admin

import toolbox.string_combinator.models as SCm

# Register your models here.
@admin.register(SCm.StringTransformationRule)
class StringTransformaationRuleAdmin(admin.ModelAdmin):
    _list_filter = [
        'deleted'
    ]
    list_display = ['__str__', 'deleted']

admin.site.register(SCm.StringTransformationSet)
admin.site.register(SCm.FailedTransformation)
