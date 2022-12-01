import numpy as n
import os
from django.shortcuts import get_object_or_404
import django

from calcapp.utils import export_results_to_xls

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vacancy.settings')
django.setup()

import calcapp.constants as c
from calcapp.models import Metal, Defect, ExperimentSettings

CONC_REL = 2.82e-4
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
            'vac': CONC_ABS,
        }
        self.sum_size_delta = None
        self.plot = []
        self.results = []

    @property
    def conc_del_dis(self):
        """
        Приток на дислокации
        """

        """
        n_vd = 3*pi*ro_d*a1^2*nu*n_v*tau*exp(-E_mv/(kT)) / (1+2*exp(-E_vd/(kT)))
        """
        flow_plus = 3 * n.pi * self.detail.metal.dis_dens * self.detail.metal.close_node ** 2 * c.DEBYE * self.concentrations['vac'] * self.exp_settings.warm_period * b_factor(-self.detail.defect.mig_ener, self.temp) / (1 + 2 * b_factor(-self.detail.defect.dis_ener, self.temp))

        """
        n_vd_ = pi*ro_d*a1^2*nu*n_vd*tau*exp(-E_mv/(kT)) / (1+0.5*exp(E_vd/(kT)))
        """
        flow_minus = n.pi * self.detail.metal.dis_dens * self.detail.metal.close_node ** 2 * c.DEBYE * self.concentrations['dis'] * self.exp_settings.warm_period * b_factor(-self.detail.defect.mig_ener, self.temp) / (1 + 0.5 * b_factor(self.detail.defect.dis_ener, self.temp))

        flow_delta = flow_plus - flow_minus  # м-3

        return flow_delta

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


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vacancy.settings')

    detail = Detail()
    experiment = Experiment(detail)

    experiment.start()
