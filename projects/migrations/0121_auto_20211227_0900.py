# Generated by Django 3.2.10 on 2021-12-27 09:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0120_auto_20211227_0838'),
    ]

    operations = [
        migrations.AddField(
            model_name='relation',
            name='name_en',
            field=models.CharField(max_length=50, null=True, verbose_name='name'),
        ),
        migrations.AddField(
            model_name='relation',
            name='name_sv',
            field=models.CharField(max_length=50, null=True, verbose_name='name'),
        ),
        migrations.AddField(
            model_name='relation',
            name='name_uk',
            field=models.CharField(max_length=50, null=True, verbose_name='name'),
        ),
    ]