# Generated by Django 2.2.2 on 2019-10-24 12:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0057_auto_20191024_1214'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='institution',
            field=models.CharField(max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='project',
            name='supported_by',
            field=models.CharField(max_length=1000, null=True),
        ),
    ]
