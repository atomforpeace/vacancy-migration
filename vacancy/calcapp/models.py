from datetime import datetime

from django.db import models

from authapp.models import SiteUser


class Metal(models.Model):
    """
    Структурные характеристика металлов
    """
    metal_name = models.CharField(max_length=30, verbose_name='Имя металла')
    gr_sarea = models.FloatField(verbose_name='Удельная площадь границ зерен, м-1')  # Sg
    tw_sarea = models.FloatField(verbose_name='Удельная площадь границ двойников, м-1')  # St
    dis_dens = models.FloatField(verbose_name='Плотность дислокаций, м-2')  # ro_d
    grid_par = models.FloatField(verbose_name='Параметр решетки, м')  # a
    close_node = models.FloatField(verbose_name='Расстояние до ближайшего узла, м')  # a1
    atomic_volume = models.FloatField(verbose_name='Атомный объем, м3', default=7.23e-31)
    # metal_length = models.FloatField(verbose_name='Размер, м', default=0.04)

    def __str__(self):
        return self.metal_name

    class Meta:
        verbose_name = 'металл'
        verbose_name_plural = 'металлы'


class Defect(models.Model):
    """
    Характеристики точечных дефектов
    """
    defect_name = models.CharField(max_length=30, verbose_name='Название')
    form_ener = models.FloatField(verbose_name='Энергия образования вакансии, эВ')  # Ev
    mig_ener = models.FloatField(verbose_name='Энергия миграции вакансии, эВ')  # Emv
    dis_ener = models.FloatField(verbose_name='Энергия связи с дислокацией, эВ')  # Evd
    gr_ener = models.FloatField(verbose_name='Энергия связи с границей зерен, эВ')  # Evg
    tw_ener = models.FloatField(verbose_name='Энергия связи с границей двойников, эВ')  # Evt
    surf_ener = models.FloatField(verbose_name='Энергия связи с поверхностью, эВ', default=0.85)  # Evs
    # dis_svol = models.FloatField(verbose_name='Удел.объем области взаимодействия с дислокацией')  # Vd
    # gr_svol = models.FloatField(verbose_name='Удел.объем области взаимодействия с границей зерей')  # Vg
    # tw_svol = models.FloatField(verbose_name='Удел.объем области взаимодействия с границей двойников')  # Vt
    surf_svol = models.FloatField(verbose_name='Удел.объем области для поверхности', default=2.2e-7)  # Vs
    clus_init_diam = models.FloatField(verbose_name='Средний начальный диаметр кластера, м')  # dc0
    clus_init_count = models.FloatField(verbose_name='Среднее начальное кол-во  v в кластере')  # nc0
    # recomb_rad = models.FloatField(verbose_name='Радиус спонтанной рекомбинации, м')  # eta

    def __str__(self):
        return self.defect_name

    class Meta:
        verbose_name = 'характеристика ТД'
        verbose_name_plural = 'характеристики ТД'


class ExperimentSettings(models.Model):
    """
    Условия эксперимента
    """
    set_name = models.CharField(max_length=30, verbose_name='Название')
    warm_period = models.FloatField(verbose_name='Время нагрева на 1 К, с')
    temp_start = models.FloatField(verbose_name='Температура в начале эксперимента, К')
    temp_stop = models.FloatField(verbose_name='Температура в конце эксперимента, К')
    time_step = models.FloatField(verbose_name='Шаг, с', default=60)
    conc_vac_start = models.FloatField(verbose_name='Начальная концентрация вакансий', default=4.6e-4)
    time_stop = models.FloatField(verbose_name='Продолжительность эксперимента, с', default=400)

    def __str__(self):
        return self.set_name

    class Meta:
        verbose_name = 'условия эксперимента'
        verbose_name_plural = 'условия эксперимента'


class Experiment(models.Model):
    user = models.ForeignKey(SiteUser, related_name='experiment', verbose_name='Пользователь', on_delete=models.CASCADE)
    metal = models.ForeignKey(Metal, verbose_name='металл', on_delete=models.CASCADE)
    defect = models.ForeignKey(Defect, verbose_name='характеристики ТД', on_delete=models.CASCADE)
    exp_settings = models.ForeignKey(ExperimentSettings, verbose_name='характеристики ТД', on_delete=models.CASCADE)
    date_time = models.DateTimeField(
        verbose_name='время эксперимента',
        default=datetime.utcnow,
    )
