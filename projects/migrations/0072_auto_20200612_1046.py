# -*- coding: utf-8 -*-
# Generated by Django 2.2.2 on 2020-06-12 10:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0071_auto_20191129_1541'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataaccesslog',
            name='flags',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='marker',
            name='color',
            field=models.CharField(choices=[('danger', 'Red'), ('success', 'Green'), ('warning', 'Yellow'), ('link', 'Dark Blue'), ('info', 'Light Blue'), ('primary', 'Teal'), ('black', 'Black'), ('grey', 'Grey')], max_length=10),
        ),
    ]
