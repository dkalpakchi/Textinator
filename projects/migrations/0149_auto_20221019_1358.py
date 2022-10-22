# -*- coding: utf-8 -*-
# Generated by Django 3.2.15 on 2022-10-19 13:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0148_auto_20221018_0742'),
    ]

    operations = [
        migrations.AddField(
            model_name='markervariant',
            name='display_tab',
            field=models.CharField(blank=True, help_text="A name of the tab to which this marker belongs (leave empty if you don't want to have any tabs)", max_length=30, null=True, verbose_name='display tab'),
        ),
        migrations.AddField(
            model_name='markervariant',
            name='display_type',
            field=models.CharField(choices=[('hl', 'Highlight'), ('und', 'Underline')], default='hl', help_text='Only applicable if annotation type is `Marker (text spans)`', max_length=3, verbose_name='display type'),
        ),
        migrations.AlterField(
            model_name='markervariant',
            name='choices',
            field=models.JSONField(blank=True, help_text='Valid only if annotation type is `radio buttons` or `checkboxes`. Up to 2 levels of nesting allowed (more than 2 is impractical for the annotator)', null=True, verbose_name='Choices for the values this marker'),
        ),
    ]