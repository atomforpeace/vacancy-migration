# Generated by Django 4.1.1 on 2022-12-27 17:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('calcapp', '0010_remove_defect_dis_svol_remove_defect_gr_svol_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='experimentsettings',
            name='temp_step',
        ),
    ]
