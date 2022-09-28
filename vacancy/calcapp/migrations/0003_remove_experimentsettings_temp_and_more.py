# Generated by Django 4.1.1 on 2022-09-06 11:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calcapp', '0002_alter_defect_options_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='experimentsettings',
            name='temp',
        ),
        migrations.AddField(
            model_name='experimentsettings',
            name='temp_start',
            field=models.FloatField(default=700, verbose_name='Температура в начале эксперимента'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='experimentsettings',
            name='temp_stop',
            field=models.FloatField(default=700, verbose_name='Температура в конце эксперимента'),
            preserve_default=False,
        ),
    ]
