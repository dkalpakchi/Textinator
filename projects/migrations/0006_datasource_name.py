# -*- coding: utf-8 -*-
# Generated by Django 2.2.2 on 2019-06-19 13:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0005_auto_20190619_1252'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasource',
            name='name',
            field=models.CharField(default='Wikipedia', max_length=50),
            preserve_default=False,
        ),
    ]
