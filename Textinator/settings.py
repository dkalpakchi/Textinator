"""
Django settings for Textinator project.

Generated by 'django-admin startproject' using Django 2.2.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
import yaml

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '^d2t^k2=%u2sh)wdrtiqtabthn&^*_%4!9*zsegm19j&2e3rz-'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    'localhost',
    'traktor.csc.kth.se'
]


# Application definition

INSTALLED_APPS = [
    'filebrowser',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'sass_processor',
    # 'prettyjson',
    'django_admin_json_editor',
    'django_registration',
    'tinymce',
    'projects',
    # 'django_extensions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'Textinator.backends.EmailAuthenticationBackend',
]

ROOT_URLCONF = 'Textinator.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'DIRS': [os.path.join(BASE_DIR, 'jinja2')],
        'APP_DIRS': True,
        'OPTIONS': {
            'environment': 'Textinator.jinja2.environment',
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ]
        },
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'libraries': {
                'common_extras': 'Textinator.templatetags.common_extras',
            },
        },
    }
]

WSGI_APPLICATION = 'Textinator.wsgi.application'

# Email
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ['TT_DB_NAME'],
        'USER': os.environ['TT_DB_USER'],
        'PASSWORD': os.environ['TT_DB_PASSWORD'],
        'HOST': os.environ['TT_DB_HOST'],
        'PORT': os.environ['TT_DB_PORT'],
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# TODO: make it more elegant
LOGOUT_REDIRECT_URL = '/textinator/accounts/login'


# Caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    },
    'context': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    },
    'input': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}



# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')
]
STATIC_URL = '/textinator/static/'
MEDIA_URL = '/textinator/media/'

MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Django Sass
SASS_PROCESSOR_ROOT = os.path.join(BASE_DIR, 'static')

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'sass_processor.finders.CssFinder',
]


# The types of tasks allowed inside the Textinator project
# TODO: handle if the file does not exist
TASK_TYPES = list(yaml.load(open(os.path.join(BASE_DIR, 'task_types.yaml')), Loader=yaml.FullLoader).items())

DATASOURCE_TYPES = [
    ('PlainText', 'Plain text'),
    ('TextFile', 'Plain text file(s)'),
    ('Db', 'Database'),
    ('Json', 'JSON file(s)')
]

MARKER_TYPES = [
    ('lb', 'Label'),
    ('rl', 'Relation')
]

MARKER_COLORS = [
    ('danger', 'Red'),
    ('success', 'Green'),
    ('warning', 'Yellow'),
    ('link', 'Dark Blue'),
    ('info', 'Light Blue'),
    ('primary', 'Teal'),
    ('black', 'Black'),
    ('grey', 'Grey')
]

LOGIN_URL = '/textinator/accounts/login/'

TINYMCE_DEFAULT_CONFIG = {
    'height': 400,
    'width': '90%',
    'cleanup_on_startup': True,
    'custom_undo_redo_levels': 20,
    'selector': 'textarea',
    'theme': 'modern',
    'plugins':'''
            textcolor save link image media preview table lists fullscreen insertdatetime
            contextmenu directionality searchreplace wordcount code fullscreen autolink lists charmap print
            ''',
    'toolbar1': '''
            fullscreen preview bold italic underline | fontselect,
            fontsizeselect  | forecolor backcolor | alignleft alignright |
            aligncenter alignjustify | indent outdent | bullist numlist table |
            | link image media | charmap |
            ''',
    'menubar': True,
    'statusbar': True,
    'relative_urls': False    
}

# TINYMCE_CALLBACKS = {
#     'file_browser_callback': 'customFileBrowser'
# }

FILEBROWSER_MAX_UPLOAD_SIZE = 20971520
