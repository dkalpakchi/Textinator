# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = "string_combinator"
urlpatterns = [
    path('', views.index, name='index'),
    path('record', views.record, name='record')
]
