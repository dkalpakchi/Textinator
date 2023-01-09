# -*- coding: utf-8 -*-
# Generated by Django 3.2.10 on 2022-01-05 07:58

from django.db import migrations, models
import django.db.models.deletion


def delete_labels_without_context(apps, schema_editor):
    Label = apps.get_model('projects', 'Label')
    Label.objects.filter(context=None).delete()


def fix_free_text_anno_types(apps, schema_editor):
    MarkerVariant = apps.get_model('projects', 'MarkerVariant')

    encountered_markers = {}

    for mv in MarkerVariant.objects.all().iterator():
        if mv.is_free_text:
            mv.anno_type = 'free-text'
            mv.save()


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0125_auto_20220103_1209'),
    ]

    operations = [
        migrations.AddField(
            model_name='markervariant',
            name='anno_type',
            field=models.CharField(choices=[('m-span', 'Marker (text spans)'), ('m-text', 'Marker (whole text)'), ('free-text', 'Free-text input'), ('integer', 'Integer'), ('float', 'Floating-point number')], default='m-span', help_text='The type of annotations made using this marker', max_length=10, verbose_name='annotation type'),
        ),
        migrations.RunPython(delete_labels_without_context, migrations.RunPython.noop),
        migrations.RunPython(fix_free_text_anno_types, migrations.RunPython.noop)
    ]