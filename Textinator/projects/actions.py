# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect


def clone_project(modeladmin, request, queryset):
    for proj in queryset:
        proj.make_clone({
            "title": "[CLONE] {}".format(proj.title)
        })
clone_project.short_description = "Clone the project"


def export_project_settings(modladmin, request, queryset):
    return HttpResponseRedirect()

export_project_settings.short_description = "Export settings & markables"
