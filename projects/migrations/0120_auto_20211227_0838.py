# Generated by Django 3.2.10 on 2021-12-27 08:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0119_auto_20211224_0910'),
    ]

    operations = [
        migrations.AddField(
            model_name='marker',
            name='name_en',
            field=models.CharField(help_text='The display name of the marker (max 50 characters)', max_length=50, null=True, verbose_name='name'),
        ),
        migrations.AddField(
            model_name='marker',
            name='name_sv',
            field=models.CharField(help_text='The display name of the marker (max 50 characters)', max_length=50, null=True, verbose_name='name'),
        ),
        migrations.AddField(
            model_name='marker',
            name='name_uk',
            field=models.CharField(help_text='The display name of the marker (max 50 characters)', max_length=50, null=True, verbose_name='name'),
        ),
    ]
