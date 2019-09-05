# Generated by Django 2.2.2 on 2019-09-04 10:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0030_auto_20190829_1314'),
    ]

    operations = [
        migrations.AddField(
            model_name='marker',
            name='type',
            field=models.CharField(choices=[('lb', 'Label'), ('rl', 'Relation')], default='lb', max_length=2),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='marker',
            name='for_task_type',
            field=models.CharField(blank=True, choices=[('qa', 'Question Answering'), ('ner', 'Named Entity Recognition'), ('corr', 'Coreference Resolution')], max_length=10),
        ),
        migrations.AlterField(
            model_name='project',
            name='task_type',
            field=models.CharField(choices=[('qa', 'Question Answering'), ('ner', 'Named Entity Recognition'), ('corr', 'Coreference Resolution')], max_length=10),
        ),
    ]
