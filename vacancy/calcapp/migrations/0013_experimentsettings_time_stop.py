# Generated by Django 4.1.1 on 2023-02-26 14:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calcapp', '0012_alter_defect_clus_init_count_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='experimentsettings',
            name='time_stop',
            field=models.FloatField(default=400, verbose_name='Продолжительность эксперимента, мин'),
        ),
    ]