# Generated by Django 2.2.2 on 2019-10-18 13:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0051_auto_20191016_0931'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='short_description',
            field=models.CharField(default='', max_length=1000),
        ),
    ]
