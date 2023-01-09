# -*- coding: utf-8 -*-
from .celery import app as celery_app

__all__ = ('celery_app',)

__version__ = '1.2.1'
VERSION = __version__  # synonym
