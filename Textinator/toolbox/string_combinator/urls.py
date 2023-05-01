# -*- coding: utf-8 -*-
from django.urls import path
from . import views


app_name = "string_combinator"
urlpatterns = [
    path('', views.index, name='index'),
    path('record/transformation/', views.record_transformation, name='record_transformation'),
    path('record/generation/', views.record_generation, name='record_generation'),
    path('search/generations/', views.search_generations, name='search_generations'),
    path('load/', views.load_generation, name='load')
]
