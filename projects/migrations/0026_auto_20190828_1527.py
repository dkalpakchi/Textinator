# Generated by Django 2.2.2 on 2019-08-28 15:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0025_marker_shortcut'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='asking_time',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='timed_questions',
            field=models.IntegerField(null=True),
        ),
    ]
