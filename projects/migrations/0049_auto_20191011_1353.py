# Generated by Django 2.2.2 on 2019-10-11 13:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0048_auto_20190927_1646'),
    ]

    operations = [
        migrations.AlterField(
            model_name='label',
            name='context',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='projects.Context'),
        ),
        migrations.AlterField(
            model_name='label',
            name='input',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='projects.Input'),
        ),
    ]
