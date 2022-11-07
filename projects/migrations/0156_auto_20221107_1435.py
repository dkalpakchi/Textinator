# -*- coding: utf-8 -*-
# Generated by Django 3.2.16 on 2022-11-07 14:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0155_batch_is_flagged'),
    ]

    operations = [
        migrations.AddField(
            model_name='input',
            name='revision_of',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='projects.input'),
        ),
        migrations.AddField(
            model_name='label',
            name='revision_of',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='projects.label'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='allowed_reviewing',
            field=models.BooleanField(default=False, help_text='Whether the annotator is allowed to review for this project', verbose_name='allowed reviewing?'),
        ),
        migrations.DeleteModel(
            name='LabelReview',
        ),
    ]
