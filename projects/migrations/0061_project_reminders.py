# Generated by Django 2.2.2 on 2019-10-28 14:43

from django.db import migrations
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0060_auto_20191025_0943'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='reminders',
            field=tinymce.models.HTMLField(blank=True, null=True),
        ),
    ]