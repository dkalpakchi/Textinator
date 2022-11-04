# -*- coding: utf-8 -*-
# Generated by Django 3.2.16 on 2022-11-04 12:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0153_markerrestriction_is_ignorable'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='editing_title_regex',
            field=models.TextField(blank=True, default='', help_text='The regular expression to be used for searching the annotated texts and using the first found result as a title of the batches to be edited', null=True, verbose_name='Regular expression for editorial board'),
        ),
    ]
