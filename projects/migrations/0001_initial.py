# -*- coding: utf-8 -*-
# Generated by Django 2.2.2 on 2019-06-18 10:11

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=50)),
                ('task_type', models.CharField(choices=[('qa', 'Question Answering')], max_length=20)),
                ('dt_publish', models.DateTimeField()),
                ('dt_finish', models.DateTimeField()),
                ('dt_updated', models.DateTimeField(auto_now=True)),
                ('collaborators', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
