# Generated by Django 2.2.2 on 2021-01-08 08:29

import django.contrib.postgres.fields.jsonb
from django.db import migrations


def set_extra_defaults(apps, schema_editor):
    Label = apps.get_model('projects', 'Label')
    for label in Label.objects.all().iterator():
        if label.comment:
            label.extra = {
                'comment': label.comment
            }
            label.save()


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0076_remove_project_allow_commenting_on_labels'),
    ]

    operations = [
        migrations.AddField(
            model_name='label',
            name='extra',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True),
        ),
        migrations.RunPython(set_extra_defaults),
        migrations.RemoveField(
            model_name='label',
            name='comment',
        ),
    ]