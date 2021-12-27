from django.urls import path
from . import views

app_name = 'users'
urlpatterns = [
    path('settings', views.user_settings, name='textinator_settings')
]