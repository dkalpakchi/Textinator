# -*- coding: utf-8 -*-
# Generated by Django 3.2.10 on 2022-04-21 13:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0140_auto_20220421_0551'),
    ]

    operations = [
        migrations.AddField(
            model_name='labelrelation',
            name='extra',
            field=models.JSONField(blank=True, help_text='in a JSON format', null=True, verbose_name='extra information'),
        ),
    ]
