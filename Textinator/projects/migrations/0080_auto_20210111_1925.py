# -*- coding: utf-8 -*-
# Generated by Django 3.1.5 on 2021-01-11 19:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0079_relation_shortcut'),
    ]

    operations = [
        migrations.AlterField(
            model_name='label',
            name='extra',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
