# Generated by Django 2.2.2 on 2019-06-18 15:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_auto_20190618_1232'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='guildeline',
            field=models.TextField(null=True),
        ),
    ]
