# -*- coding: utf-8 -*-
# Generated by Django 3.2.16 on 2022-12-13 18:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0159_auto_20221107_1942'),
    ]

    operations = [
        migrations.AddField(
            model_name='batch',
            name='revision_changes',
            field=models.TextField(default='', help_text='The list of exact changes that were done to the object', verbose_name='revision changes'),
        ),
        migrations.AddField(
            model_name='input',
            name='revision_changes',
            field=models.TextField(default='', help_text='The list of exact changes that were done to the object', verbose_name='revision changes'),
        ),
        migrations.AddField(
            model_name='label',
            name='revision_changes',
            field=models.TextField(default='', help_text='The list of exact changes that were done to the object', verbose_name='revision changes'),
        ),
    ]