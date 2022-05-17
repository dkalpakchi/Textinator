# Generated by Django 3.2.10 on 2022-01-09 16:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0128_auto_20220109_1642'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='markerunit',
            name='name',
        ),
        migrations.RemoveField(
            model_name='relation',
            name='project',
        ),
        migrations.RemoveField(
            model_name='labelrelation',
            name='rule',
        ),
        migrations.RenameField(
            model_name='labelrelation',
            old_name='rule_v',
            new_name='rule',
        ),
        migrations.AlterField(
            model_name='labelrelation',
            name='rule',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.RelationVariant'),
        ),
    ]
