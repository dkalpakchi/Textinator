# -*- coding: utf-8 -*-
from django.db import models, connection


class RegConfigField(models.Field):
    def db_type(self, connection):
        return 'regconfig'


# based on: https://stackoverflow.com/questions/2317452/django-count-rawqueryset
def rawqueryset_count(query, params):
    sql = 'SELECT COUNT(*) FROM ({}) T;'
    cursor = connection.cursor()
    cursor.execute(sql.format(query), params)
    row = cursor.fetchone()
    return row[ 0 ]
