# -*- coding: utf-8 -*-
# Generated by Django 3.2.16 on 2023-01-25 14:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('toolbox_string_combinator', '0002_auto_20230117_2008'),
    ]

    operations = [
        migrations.AddField(
            model_name='stringtransformationrule',
            name='deleted',
            field=models.BooleanField(default=False),
        ),
    ]
