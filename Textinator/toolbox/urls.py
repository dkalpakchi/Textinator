# -*- coding: utf-8 -*-
from django.urls import path, include
from . import views

app_name = 'toolbox'
urlpatterns = [
    path('scombinator/', include('toolbox.string_combinator.urls')),
]
