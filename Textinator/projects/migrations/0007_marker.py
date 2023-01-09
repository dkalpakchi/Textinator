# -*- coding: utf-8 -*-
# Generated by Django 2.2.2 on 2019-06-19 13:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0006_datasource_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Marker',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=50)),
                ('color', models.CharField(choices=[('danger', 'Red'), ('success', 'Green'), ('warning', 'Yellow'), ('link', 'Dark Blue'), ('info', 'Light Blue'), ('primary', 'Teal'), ('black', 'Black')], max_length=10)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.Project')),
            ],
        ),
    ]