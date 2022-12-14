# Generated by Django 4.1.1 on 2022-09-27 17:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calcapp', '0003_remove_experimentsettings_temp_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='defect',
            old_name='name',
            new_name='defect_name',
        ),
        migrations.RenameField(
            model_name='experimentsettings',
            old_name='name',
            new_name='set_name',
        ),
        migrations.RenameField(
            model_name='metal',
            old_name='name',
            new_name='metal_name',
        ),
        migrations.AlterField(
            model_name='defect',
            name='clus_init_diam',
            field=models.FloatField(verbose_name='Средний начальный диаметр кластера'),
        ),
        migrations.AlterField(
            model_name='defect',
            name='tw_svol',
            field=models.FloatField(verbose_name='Удел.объем области взаимодействия с границей двойников'),
        ),
    ]
