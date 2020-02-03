from django.urls import path
from . import views

app_name = 'projects'
urlpatterns = [
	path('participations/update', views.update_participations, name="update_participations"),
    path('<proj>/article/new', views.new_article, name='new_article'),
    path('<proj>/article/undo_last', views.undo_last, name='undo_last'),
    path('<proj>/record_datapoint/', views.record_datapoint, name="record_datapoint"),
    path('<proj>/join', views.join_or_leave_project, name='join_or_leave'),
    path('<proj>/explorer', views.data_explorer, name='data_explorer'),
    path('<proj>/export', views.export, name='data_explorer'),
    path('<proj>/explorer/inputs/<inp>/delete', views.async_delete_input, name='async_delete_input'),
    path('profile/<username>/', views.profile, name='profile'),
    path('<pk>/', views.DetailView.as_view(), name='detail'),
    path('', views.IndexView.as_view(), name='index')
]