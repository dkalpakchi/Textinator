# Generated by Django 3.2.10 on 2021-12-23 13:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20201202_1438'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='profile',
            options={'verbose_name': 'profile', 'verbose_name_plural': 'profiles'},
        ),
        migrations.AlterField(
            model_name='profile',
            name='language',
            field=models.CharField(default='en', max_length=5, verbose_name='language'),
        ),
    ]