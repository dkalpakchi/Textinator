# Generated by Django 2.2.2 on 2019-06-19 15:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0008_auto_20190619_1409'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataPoint',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('context', models.TextField(null=True)),
                ('input_data', models.TextField()),
            ],
        ),
        migrations.RenameField(
            model_name='marker',
            old_name='label',
            new_name='label_name',
        ),
        migrations.AddField(
            model_name='marker',
            name='short',
            field=models.CharField(help_text='By default the capitalized first three character of the label', max_length=5, null=True),
        ),
        migrations.CreateModel(
            name='Label',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.PositiveIntegerField(null=True)),
                ('end', models.PositiveIntegerField(null=True)),
                ('datapoint', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.DataPoint')),
                ('marker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.Marker')),
            ],
        ),
    ]
