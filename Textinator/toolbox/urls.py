# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = 'toolbox'
urlpatterns = [
    path('scombinator', views.string_combinator, name='string_combinator'),
]
