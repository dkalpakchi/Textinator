# -*- coding: utf-8 -*-
# Generated by Django 3.1.5 on 2021-01-25 11:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0085_auto_20210125_1142'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='markercontextmenuitem',
            name='admin_filter',
        ),
        migrations.AddField(
            model_name='markeraction',
            name='admin_filter',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
