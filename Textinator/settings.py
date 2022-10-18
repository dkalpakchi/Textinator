"""
Django settings for Textinator project.

Generated by 'django-admin startproject' using Django 2.2.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
import glob
import secrets

from django.utils.translation import gettext_lazy as _

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(secrets.randbelow(28) + 8))

DEBUG = int(os.environ.get("DEBUG", default=0))

COMPRESS_ENABLED = False

# 'DJANGO_ALLOWED_HOSTS' should be a single string of hosts with a space between each.
# For example: 'DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]'
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(" ")

# Application definition

INSTALLED_APPS = [
    'jazzmin',
    'filebrowser',
    'modeltranslation',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "compressor",
    # 'prettyjson',
    'django_registration',
    'tinymce',
    'chartjs',
    'projects',
    'rangefilter',
    # 'surveys'
    # 'django_extensions',
    'nested_admin',
    'scientific_survey',
    'users',
    'colorfield',
    'rosetta',
    'guardian'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'Textinator.backends.EmailAuthenticationBackend',
    'guardian.backends.ObjectPermissionBackend',
]

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

ROOT_URLCONF = 'Textinator.urls'
ROOT_URLPATH = os.environ.get("ROOT_URLPATH", "")

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
                'projects.context_processors.common_user_variables'
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
                'projects.context_processors.common_user_variables'
            ],
            'libraries': {
                'common_extras': 'Textinator.templatetags.common_extras',
                'survey_extras': 'scientific_survey.templatetags.survey_extras'
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
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('TT_DB_NAME'),
        'USER': os.environ.get('TT_DB_USER'),
        'PASSWORD': os.environ.get('TT_DB_PASSWORD'),
        'HOST': os.environ.get('TT_DB_HOST'),
        'PORT': os.environ.get('TT_DB_PORT'),
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
LOGOUT_REDIRECT_URL = '/{}accounts/login'.format(ROOT_URLPATH)


# Caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211',
    },
    'context': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211',
    }
}



# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

# Codes must be compliant with RFC 5646
# (see http://www.iana.org/assignments/language-subtag-registry/language-subtag-registry for the whole list of language codes)
LANGUAGES = [
    ('en', 'English'),
    ('nl', 'Dutch'),
    ('ru', 'Russian'),
    ('es', 'Spanish'),
    ('sv', 'Swedish'),
    ('uk', 'Ukrainian')
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
] + glob.glob(os.path.join(BASE_DIR, 'locale', 'custom', '*'))

LANGUAGE_CODE = 'en'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

ROSETTA_LANGUAGE_GROUPS = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'node_modules')
]
STATIC_URL = '/{}static/'.format(ROOT_URLPATH)
MEDIA_URL = '/{}media/'.format(ROOT_URLPATH)
STATIC_ROOT = 'static_cdn'

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
UPLOAD_DIR = os.path.join(MEDIA_ROOT, 'uploads')

if not os.path.exists(MEDIA_ROOT):
    os.makedirs(MEDIA_ROOT)

if not os.path.exists(UPLOAD_DIR):
    os.mkdir(UPLOAD_DIR)

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder'
]

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

FILEBROWSER_MAX_UPLOAD_SIZE = 20971520 # 20MB


pdfmetrics.registerFont(TTFont('ROBOTECH GP',
    os.path.join(BASE_DIR, 'static', 'styles', 'webfonts', 'ROBOTECH GP.ttf')))


CHOICES_SEPARATOR = "|"

JAZZMIN_SETTINGS = {
    # title of the window (Will default to current_admin_site.site_title if absent or None)
    "site_title": "Textinator Admin",
    # Title on the login screen (19 chars max) (defaults to current_admin_site.site_header if absent or None)
    "site_header": "Textinator Admin",
    # Copyright on the footer
    "copyright": "Dmytro Kalpakchi",
    # Links to put along the top menu
    "topmenu_links": [

        # Url that gets reversed (Permissions can be added)
        {"name": _("Back to the site"),  "url": '/{}'.format(ROOT_URLPATH)}#reverse('projects:index')},
    ],
    "language_chooser": True,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": False,
    "accent": "accent-lightblue",
    "navbar": "navbar-info navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-outline-info",
        "warning": "btn-outline-warning",
        "danger": "btn-outline-danger",
        "success": "btn-outline-success"
    },
    "actions_sticky_top": True
}

# Textinator settings
DATA_DIRS = [
    os.path.join(BASE_DIR, 'data'),
    os.path.join(MEDIA_ROOT, 'uploads', "{username}")
]

NOTEBOOK_DIR = os.path.join(MEDIA_ROOT, 'uploads', "{username}", "notebooks")

DATA_UPLOAD_MAX_NUMBER_FIELDS = 20240
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600 # 100MB

# The types of tasks allowed inside the Textinator project
TASK_TYPES = [
    ('generic', 'Generic'),
    ('qa', 'Question Answering'),
    ('qar', 'Question Answering with Ranking'),
    ('mcqa', 'Multiple Choice Question Answering'),
    ('mcqar', 'Multiple Choice Question Answering with Ranking'),
    ('ner', 'Named Entity Recognition'),
    ('pronr', 'Pronoun Resolution'),
    ('corr', 'Coreference Resolution'),
    ('mt', 'Machine Translation')
]

DATASOURCE_TYPES = [
    ('PlainText', 'Plain text'),
    ('TextFile', 'Plain text file(s)'),
    ('Json', 'JSON file(s)'),
    ('DialJSL', 'Dialogue JSON lines'),
    ('TextsAPI', 'Texts API')
]

FORMATTING_TYPES = [
    ('md', 'Markdown'),
    ('ft', 'Formatted text'),
    ('pt', 'Plain text')
]

ANNOTATION_TYPES = [
    ('m-span', 'Marker (text spans)'),
    ('m-text', 'Marker (whole text)'),
    ('free-text', 'Short free-text input'),
    ('lfree-text', 'Long free-text input'),
    ('integer', 'Integer'),
    ('float', 'Floating-point number'),
    ('range', 'Range'),
    ('radio', 'Radio buttons'),
    ('check', 'Checkboxes')
]

LOGIN_URL = '/{}accounts/login/'.format(ROOT_URLPATH)

FILEBROWSER_EXTENSIONS = {
    'Image': ['.jpg','.jpeg','.gif','.png','.tif','.tiff'],
    'Document': ['.pdf','.doc','.rtf','.txt','.xls','.csv', '.json', '.jsonl'],
    'Video': ['.mov','.wmv','.mpeg','.mpg','.avi','.rm'],
    'Audio': ['.mp3','.mp4','.wav','.aiff','.midi','.m4p']
}
