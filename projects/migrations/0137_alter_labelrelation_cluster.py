# -*- coding: utf-8 -*-
# Generated by Django 3.2.10 on 2022-01-15 16:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0136_auto_20220115_0925'),
    ]

    operations = [
        migrations.AlterField(
            model_name='labelrelation',
            name='cluster',
            field=models.PositiveIntegerField(default=1, help_text='At the submission time', verbose_name='relation cluster'),
        ),
    ]
