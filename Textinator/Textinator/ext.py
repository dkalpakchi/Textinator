# -*- coding: utf-8 -*-
from django.db import models


class RegConfigField(models.Field):
    def db_type(self, connection):
        return 'regconfig'
