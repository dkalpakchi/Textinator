# Generated by Django 3.2.10 on 2021-12-23 13:44

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def change_markers_to_variants(apps, schema_editor):
    Marker = apps.get_model('projects', 'Marker')
    MarkerVariant = apps.get_model('projects', 'MarkerVariant')
    MarkerContextMenuItem = apps.get_model('projects', 'MarkerContextMenuItem')

    encountered_markers = {}
    
    for mv in MarkerVariant.objects.all().iterator():
        if mv.marker.code in encountered_markers:
            for a_id in encountered_markers[mv.marker.code]:
                cm_item = encountered_markers[mv.marker.code][a_id]
                MarkerContextMenuItem.objects.create(
                    marker=mv.marker,
                    markerv=mv,
                    action_id=a_id,
                    verbose=cm_item.verbose,
                    verbose_admin=cm_item.verbose_admin,
                    field=cm_item.field,
                    config=cm_item.config
                )
        else:
            actions = mv.marker.actions.all()
            encountered_markers[mv.marker.code] = {}
            for a in actions:
                cm_item = MarkerContextMenuItem.objects.filter(marker=mv.marker, action=a).first()
                cm_item.markerv = mv
                cm_item.save()
                encountered_markers[mv.marker.code][a.pk] = cm_item

    MarkerContextMenuItem.objects.filter(markerv_id=None).delete()



class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0116_auto_20211223_1334'),
    ]

    operations = [
        migrations.AddField(
            model_name='markervariant',
            name='actions',
            field=models.ManyToManyField(blank=True, help_text='Actions associated with this marker', through='projects.MarkerContextMenuItem', to='projects.MarkerAction', verbose_name='marker actions'),
        ),
        migrations.AddField(
            model_name='markercontextmenuitem',
            name='markerv',
            field=models.ForeignKey(db_index=False, blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='projects.markervariant', verbose_name='marker'),
        ),
        migrations.RunPython(change_markers_to_variants, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='marker',
            name='actions',
        ),
    ]
