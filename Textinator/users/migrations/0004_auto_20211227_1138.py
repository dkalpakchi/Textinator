# -*- coding: utf-8 -*-
# Generated by Django 3.2.10 on 2021-12-27 11:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_auto_20211223_1334'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='language',
        ),
        migrations.AddField(
            model_name='profile',
            name='fluent_in',
            field=models.TextField(default='en', help_text='Comma-separated list of language codes, compliant with RFC 5646', verbose_name='fluent in'),
        ),
        migrations.AddField(
            model_name='profile',
            name='preferred_language',
            field=models.CharField(choices=[('en', 'English'), ('sv', 'Swedish'), ('uk', 'Ukrainian')], default='en', max_length=10, verbose_name='preferred language'),
        ),
    ]