# -*- coding: utf-8 -*-
from django.contrib import admin

import toolbox.string_combinator.models as SCm

# Register your models here.

admin.site.register(SCm.StringTransformationRule)
admin.site.register(SCm.StringTransformationSet)
admin.site.register(SCm.FailedTransformation)
