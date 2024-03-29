# -*- coding: utf-8 -*-
# Generated by Django 3.1.5 on 2021-12-13 10:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0112_auto_20211201_1243'),
    ]

    operations = [
        migrations.AddField(
            model_name='marker',
            name='code',
            field=models.CharField(blank=True, help_text="Marker's nickname used internally", max_length=25),
        ),
        migrations.AlterField(
            model_name='marker',
            name='name',
            field=models.CharField(help_text='The display name of the marker (max 50 characters, must be unique)', max_length=50),
        ),
    ]
