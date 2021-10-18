# Generated by Django 2.2.2 on 2019-09-05 14:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0034_auto_20190905_1426'),
    ]

    operations = [
        migrations.AlterField(
            model_name='relation',
            name='direction',
            field=models.CharField(choices=[('0', 'Directed from the first to the second'), ('1', 'Directed from the second to the first'), ('2', 'Bi-directional')], max_length=1),
        ),
    ]
