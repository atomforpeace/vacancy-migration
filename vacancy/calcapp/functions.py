import numpy as n
import os
from django.shortcuts import get_object_or_404
import django

from django.forms.models import model_to_dict

from calcapp.utils import export_results_to_xls

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vacancy.settings')
django.setup()

import calcapp.constants as c
from calcapp.models import Metal, Defect, ExperimentSettings

# CONC_REL = 2.82e-4
CONC_REL = 4.6e-4
CONC_ABS = 4.18e25
VS = 2.2e-7
EVC = 0.05  # Что это?

NV1C = 47.3
NC0 = 4.42e22


def b_factor(energy, temp):
    """
    Множитель Больцмана
    """
    return n.exp(energy * c.K_J_EV / (temp * c.BOLTZMANN))


def conc_abs_to_rel(conc_abs, grid_par):
    """
    Перевод концентрации из абсолютных единиц в относительные
    n_v -> c_v
    """
    return conc_abs * grid_par ** 3 / 2


def conc_rel_to_abs(conc_rel, grid_par):
    """
    Перевод концентрации из относительных единиц в абсолютные
    c_v -> n_v
    """
    return 2 * conc_rel / grid_par ** 3


class Detail:
    """
    Образец
    """
    def __init__(self, metal=None, defect=None):
        self.metal = metal
        self.defect = defect

    def vol_change(self, ener):
        """
        Дельта энергии
        """
        return ener / self.defect.form_ener * 0.15

    @property
    def volume_delta(self):
        """
        Изменение объема
        """
        return {
            'dis': self.vol_change(ener=self.defect.dis_ener),
            'gr': self.vol_change(ener=self.defect.gr_ener),
            'tw': self.vol_change(ener=self.defect.tw_ener),
            'clus': self.vol_change(ener=EVC),
        }

    @property
    def volume(self):
        return self.metal.grid_par ** 3 / 2


class Experiment:
    """
    Эксперимент
    """

    def __init__(self, detail, exp_settings):
        self.detail = detail
        self.exp_settings = exp_settings
        self.temp = self.exp_settings.temp_start
        self.rel_volume_clus = NV1C
        self.concentrations = {
            'dis': 0,
            'gr': 0,
            'tw': 0,
            'vac': conc_rel_to_abs(self.exp_settings.conc_vac_start, self.detail.metal.grid_par),
        }
        self.sum_size_delta = None
        self.plot = []
        self.results = []

        self.delta_time = 1

    @property
    def conc_dis_plus(self):
        """
        Приток на дислокации
        """

        probability = 1 / (1 + 2 * b_factor(-self.detail.defect.dis_ener, self.temp))
        unit_volume = 3 * n.pi * self.detail.metal.dis_dens * self.detail.metal.close_node ** 2

        """
        n_vd = 3*pi*ro_d*a1^2*nu*n_v*tau*exp(-E_mv/(kT)) / (1+2*exp(-E_vd/(kT)))
        """
        flow_plus = unit_volume * probability * self.concentrations['vac'] * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp)

        return flow_plus

    @property
    def conc_dis_minus(self):
        """
        Отток с дислокаций
        """

        probability = 1 / (1 + 0.5 * b_factor(-self.detail.defect.dis_ener, self.temp))
        unit_volume = n.pi * self.detail.metal.dis_dens * self.detail.metal.close_node ** 2

        """
        n_vd_ = pi*ro_d*a1^2*nu*n_vd*tau*exp(-E_mv/(kT)) / (1+0.5*exp(E_vd/(kT)))
        """
        flow_minus = unit_volume * probability * self.concentrations['dis'] * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp)

        return flow_minus

    @property
    def conc_del_gr(self):
        """
        Приток на зерна
        """

        """
        n_vg = 2*S_g*a1*nu*n_v*tau*exp(-E_mv/(kT)) / (1+exp(-E_vg/(kT)))
        """
        flow_plus = 2 * self.detail.metal.gr_sarea * self.detail.metal.close_node * c.DEBYE * self.concentrations['vac'] * self.exp_settings.warm_period * b_factor(-self.detail.defect.mig_ener, self.temp) / (1 + b_factor(-self.detail.defect.gr_ener, self.temp))

        """
        n_vg_ = 2*S_g*a1*nu*n_g*tau*exp(-E_mv/(kT)) / (1+exp(E_vg/(kT)))
        """
        flow_minus = 2 * self.detail.metal.gr_sarea * self.detail.metal.close_node * c.DEBYE * self.concentrations['gr'] * self.exp_settings.warm_period * b_factor(-self.detail.defect.mig_ener, self.temp) / (1 + b_factor(self.detail.defect.gr_ener, self.temp))

        flow_delta = flow_plus - flow_minus  # м-3

        return flow_delta

    @property
    def conc_gr_plus(self):
        """
        Приток на зерна
        """

        probability = 1 / (1 + b_factor(-self.detail.defect.gr_ener, self.temp))
        unit_volume = 2 * self.detail.metal.gr_sarea * self.detail.metal.close_node

        """
        n_vg = 2*S_g*a1*nu*n_v*tau*exp(-E_mv/(kT)) / (1+exp(-E_vg/(kT)))
        """
        flow_plus = unit_volume * probability * self.concentrations['vac'] * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp)

        return flow_plus

    @property
    def conc_gr_minus(self):
        """
        Отток с зерен
        """

        probability = 1 / (1 + b_factor(self.detail.defect.gr_ener, self.temp))
        unit_volume = 2 * self.detail.metal.gr_sarea * self.detail.metal.close_node

        """
        n_vg_ = 2*S_g*a1*nu*n_g*tau*exp(-E_mv/(kT)) / (1+exp(E_vg/(kT)))
        """
        flow_minus = unit_volume * probability * self.concentrations['gr'] * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp)

        return flow_minus

    @property
    def conc_tw_plus(self):
        """
        Приток на двойники
        """

        probability = 1 / (1 + b_factor(-self.detail.defect.tw_ener, self.temp))
        unit_volume = 2 * self.detail.metal.tw_sarea * self.detail.metal.close_node

        """
        n_vg = 2*S_t*a1*nu*n_v*tau*exp(-E_mv/(kT)) / (1+exp(-E_vg/(kT)))
        """
        flow_plus = unit_volume * probability * self.concentrations['vac'] * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp)

        return flow_plus

    @property
    def conc_tw_minus(self):
        """
        Отток с двойников
        """

        probability = 1 / (1 + b_factor(-self.detail.defect.tw_ener, self.temp))
        unit_volume = 2 * self.detail.metal.tw_sarea * self.detail.metal.close_node

        """
        n_vg_ = 2*S_t*a1*nu*n_t*tau*exp(-E_mv/(kT)) / (1+exp(E_vg/(kT)))
        """
        flow_minus = unit_volume * probability * self.concentrations['tw'] * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp)

        return flow_minus

    @property
    def conc_del_tw(self):
        """
        Приток на двойники
        """

        """
        n_vg = 2*S_t*a1*nu*n_v*tau*exp(-E_mv/(kT)) / (1+exp(-E_vg/(kT)))
        """
        flow_plus = 2 * self.detail.metal.tw_sarea * self.detail.metal.close_node * c.DEBYE * self.concentrations['vac'] * self.exp_settings.warm_period * b_factor(-self.detail.defect.mig_ener, self.temp) / (1 + b_factor(-self.detail.defect.tw_ener, self.temp))

        """
        n_vg_ = 2*S_t*a1*nu*n_t*tau*exp(-E_mv/(kT)) / (1+exp(E_vg/(kT)))
        """
        flow_minus = 2 * self.detail.metal.tw_sarea * self.detail.metal.close_node * c.DEBYE * self.concentrations['tw'] * self.exp_settings.warm_period * b_factor(-self.detail.defect.mig_ener, self.temp) / (1 + b_factor(self.detail.defect.tw_ener, self.temp))

        flow_delta = flow_plus - flow_minus  # м-3

        return flow_delta

    @property
    def conc_del_clus(self):
        """
        Приток из кластеров
        """

        """
        n_c = N_v1c*(a1/d_c0)^2*nu*n_c0 / (6*exp((E_mv+E_vc)/(kT)) 
        """

        flow = self.rel_volume_clus * (self.detail.metal.close_node / self.detail.defect.clus_init_diam) ** 2 * c.DEBYE / 6 * \
            b_factor(-(self.detail.defect.mig_ener + EVC), self.temp) * NC0

        return flow

    @property
    def conc_del_s(self):
        """
        Пока не известный приток
        """

        flow = VS * c.DEBYE * CONC_ABS * self.detail.metal.grid_par ** 3 / 2 * b_factor(-(self.detail.defect.mig_ener + EVC),
                                                                                 self.temp)

        return flow

    def start(self):

        plot_x = []
        plot_y = []

        size_delta = {
            'dis': 0,
            'gr': 0,
            'tw': 0,
            'clus': 0,
            's': 0,
        }

        t = self.exp_settings.temp_start

        while t <= self.exp_settings.temp_stop:
            # print(f'Расчет для температуры {t} K')
            self.temp = t

            del_conc = {
                'dis': self.conc_del_dis,
                'gr': self.conc_del_gr,
                'tw': self.conc_del_tw,
                'clus': self.conc_del_clus,
            }

            # print(del_conc)

            for type_ in ('dis', 'gr', 'tw'):
                self.concentrations[type_] += del_conc[type_]
            self.concentrations['vac'] -= del_conc['dis'] + del_conc['gr'] + del_conc['tw'] - del_conc['clus']

            # print(self.concentrations)

            for type_ in ('dis', 'gr', 'tw', 'clus'):
                size_delta[type_] += del_conc[type_] * self.detail.volume_delta[type_] * self.detail.volume

            self.sum_size_delta = sum(size_delta.values())

            self.plot.append([t, self.sum_size_delta])

            # self.concentrations['vac'] -= del_conc['dis'] + del_conc['gr'] + del_conc['tw'] - del_conc['clus']

            # print(self.sum_size_delta)

            self.results.append(
                {
                    'T': self.temp,
                    'nvd': del_conc['dis'],
                    'nvg': del_conc['gr'],
                    'nvt': del_conc['tw'],
                    'nv': del_conc['clus'],
                    'Dcv': self.sum_size_delta,
                }
            )

            t += self.exp_settings.warm_period / 60

        return export_results_to_xls(self.results), self.plot

    def start_dis_only(self):
        """
        Решение задачи Коши методом Эйлера
        """

        # Устанавливаем температуру равной начальной из БД
        self.temp = self.exp_settings.temp_start

        # Расчет шага температуры
        delta_T = self.exp_settings.time_step / 60

        # Переменная номера шага для информативности
        step_count = 0

        # Выполняем расчет концентраций по шагам
        while self.temp <= self.exp_settings.temp_stop and self.concentrations["vac"] > 0:
            # Расчет концентрации на дислокациях
            dis_delta = self.conc_dis_plus - self.conc_dis_minus
            self.concentrations["dis"] += dis_delta
            # Расчет концентрации на зернах
            gr_delta = self.conc_gr_plus - self.conc_gr_minus
            self.concentrations["gr"] += gr_delta
            # Расчет концентрации на двойниках
            tw_delta = self.conc_tw_plus - self.conc_tw_minus
            self.concentrations["tw"] += tw_delta
            # Расчет концентрации вакансий с учетом потоком на/с стоки
            self.concentrations["vac"] -= dis_delta + gr_delta + tw_delta
            # print('==========================\n')
            self.temp += delta_T
            step_count += 1

            self.results.append(
                {
                    'T': self.temp,
                    'con_dis': self.concentrations['dis'],
                    'con_gr': self.concentrations['gr'],
                    'con_tw': self.concentrations['tw'],
                    'con_vac': self.concentrations['vac'],
                }
            )

            self.plot.append(list(self.concentrations.values()))

        return self.results


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vacancy.settings')

    defect = get_object_or_404(Defect, pk=1)
    # defect = model_to_dict(obj)

    metal = get_object_or_404(Metal, pk=1)
    # metal = model_to_dict(obj)

    settings = get_object_or_404(ExperimentSettings, pk=1)
    # settings = model_to_dict(obj)

    detail = Detail(metal=metal, defect=defect)

    experiment = Experiment(detail, settings)

    plot_values = experiment.start_dis_only()
