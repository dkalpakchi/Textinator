# Generated by Django 2.2.2 on 2019-09-04 10:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0032_auto_20190904_1043'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marker',
            name='shortcut',
            field=models.CharField(blank=True, help_text='Keyboard shortcut for marking a piece of text with this label', max_length=10, null=True),
        ),
    ]
