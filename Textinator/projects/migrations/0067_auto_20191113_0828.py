# -*- coding: utf-8 -*-
# Generated by Django 2.2.2 on 2019-11-13 08:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0066_dataaccesslog_accessed_datapoints'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataaccesslog',
            name='accessed_datapoints',
            field=models.PositiveIntegerField(blank=True, default=0, null=True),
        ),
        migrations.AlterField(
            model_name='dataaccesslog',
            name='last_datapoint',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]