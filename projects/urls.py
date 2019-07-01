from django.urls import path
from . import views

app_name = 'projects'
urlpatterns = [
    path('<proj>/article/new', views.new_article, name='new_article'),
    path('profile/<username>/', views.profile, name='profile'),
    path('record_datapoint/', views.record_datapoint, name="record_datapoint"),
    path('<pk>/', views.DetailView.as_view(), name='detail'),
    path('', views.IndexView.as_view(), name='index')
]