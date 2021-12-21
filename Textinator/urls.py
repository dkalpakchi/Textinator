"""Textinator URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin, auth
from django.urls import path, include, reverse, re_path
from django_registration.backends.one_step.views import RegistrationView
from django.views.generic import RedirectView

from filebrowser.sites import site

from . import views


urlpatterns = [
    path('textinator/', include([
        path('', views.index),
        path('admin/filebrowser/', site.urls),
        path('admin/', admin.site.urls),
        path('accounts/register/',
            RegistrationView.as_view(success_url='/textinator/'),
            name='django_registration_register'),
        path('accounts/', include('django_registration.backends.one_step.urls')),
        path('accounts/', include('django.contrib.auth.urls')),
        path('projects/', include('projects.urls')),
        path('tinymce/', include('tinymce.urls')),
        path('survey/', include('survey.urls')),
        path('users/', include('users.urls')),
        path('i18n/', include('django.conf.urls.i18n')),
    ]))
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += [
        re_path(r'^rosetta/', include('rosetta.urls'))
    ]

