# Generated by Django 2.2.2 on 2021-01-05 13:44

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0074_project_disable_submitted_labels'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarkerAction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dt_created', models.DateTimeField(default=django.utils.timezone.now, null=True, verbose_name='creation date')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('description', models.TextField()),
                ('file', models.CharField(max_length=100)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MarkerContextMenuItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dt_created', models.DateTimeField(default=django.utils.timezone.now, null=True, verbose_name='creation date')),
                ('verbose', models.CharField(max_length=50)),
                ('action', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.MarkerAction')),
                ('marker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.Marker')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='marker',
            name='actions',
            field=models.ManyToManyField(blank=True, through='projects.MarkerContextMenuItem', to='projects.MarkerAction'),
        ),
    ]
