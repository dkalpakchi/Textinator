# Generated by Django 2.2.2 on 2019-06-20 07:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0012_auto_20190620_0743'),
    ]

    operations = [
        migrations.AddField(
            model_name='input',
            name='content_hash',
            field=models.CharField(default=1, max_length=32),
            preserve_default=False,
        ),
    ]
