# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = 'projects'
urlpatterns = [
    #path("exports/settings", views.export_settings, name="export_settings"),
    path("import/", views.importer, name='import'),
    path('<proj>/flag/text', views.flag_text, name='flag_text'),
    path('<proj>/flag/batch', views.flag_batch, name='flag_batch'),
    path('<proj>/flagged/search', views.flagged_search, name='flagged_search'),
    path('<proj>/recorded/search', views.recorded_search, name='recorded_search'),
    path('<proj>/article/new', views.new_article, name='new_article'),
    path('<proj>/article/undo_last', views.undo_last, name='undo_last'),
    path('<proj>/record_datapoint/', views.record_datapoint, name="record_datapoint"),
    path('<proj>/edit/', views.editing, name="editing"),
    path('<proj>/review/', views.review, name='review'),
    path('<proj>/join', views.join_or_leave_project, name='join_or_leave'),
    path('<proj>/time_report', views.time_report, name='time_report'),
    path('<proj>/explorer', views.data_explorer, name='data_explorer'),
    path('<proj>/export', views.export, name='data_exporter'),
    path('<proj>/explorer/inputs/<inp>/delete', views.async_delete_input, name='async_delete_input'),
    path("<proj>/get/annotations", views.get_annotations, name="get_annotations"),
    path("<proj>/get/context", views.get_context, name="get_context"),
    path("<proj>/get/batch", views.get_batch, name="get_batch"),
    path('profile/<username>/', views.profile, name='profile'),
    path('<pk>/', views.DetailView.as_view(), name='detail'),
    path("<pk>/chart/start", views.chart_start, name="chart_start"),
    path("<pk>/chart/status", views.chart_status, name="chart_status"),
    #path("<pk>/charts/users/timing", views.user_timing_chart_json, name="user_timing_chart"),
    #path("<pk>/charts/users/progress", views.user_progress_chart_json, name="user_progress_chart"),
    #path("<pk>/charts/datasources/sizes", views.datasource_size_chart_json, name="datasource_size_chart"),
    path("get/data/<source_id>/<dp_id>", views.get_data, name="get_data"),
    path('', views.IndexView.as_view(), name='index')
]
