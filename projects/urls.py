from django.urls import path
from . import views

urlpatterns = [
    path('record_datapoint/', views.record_datapoint, name="record_datapoint"),
    path('<pk>/', views.DetailView.as_view(), name='detail'),
    path('', views.IndexView.as_view(), name='index')
]