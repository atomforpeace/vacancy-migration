# Generated by Django 4.1.1 on 2023-04-26 15:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calcapp', '0013_experimentsettings_time_stop'),
    ]

    operations = [
        migrations.AddField(
            model_name='metal',
            name='atomic_volume',
            field=models.FloatField(default=7.23e-31, verbose_name='Атомный объем, м3'),
        ),
        migrations.AddField(
            model_name='metal',
            name='metal_length',
            field=models.FloatField(default=0.04, verbose_name='Размер, м'),
        ),
        migrations.AlterField(
            model_name='experimentsettings',
            name='time_stop',
            field=models.FloatField(default=400, verbose_name='Продолжительность эксперимента, с'),
        ),
    ]