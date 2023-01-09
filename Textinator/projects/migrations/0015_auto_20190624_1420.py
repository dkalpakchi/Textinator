# -*- coding: utf-8 -*-
# Generated by Django 2.2.2 on 2019-06-24 14:20

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0014_auto_20190624_1314'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='input',
            name='content_hash',
        ),
        migrations.AddField(
            model_name='userprofile',
            name='project',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='projects.Project'),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name='project',
            name='participants',
        ),
        migrations.AddField(
            model_name='project',
            name='participants',
            field=models.ManyToManyField(related_name='participations', through='projects.UserProfile', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='profiles', to=settings.AUTH_USER_MODEL),
        ),
    ]