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
            'surf': 0,
            'vac': conc_rel_to_abs(self.exp_settings.conc_vac_start, self.detail.metal.grid_par),
        }

        self.conc_const = conc_rel_to_abs(self.exp_settings.conc_vac_start, self.detail.metal.grid_par)

        self.results = []

        self.volumes = {
            'dis_plus': 3 * n.pi * self.detail.metal.dis_dens * self.detail.metal.close_node ** 2,
            'dis_minus': n.pi * self.detail.metal.dis_dens * self.detail.metal.close_node ** 2,
            'tw': 2 * self.detail.metal.tw_sarea * self.detail.metal.close_node,
            'gr': 2 * self.detail.metal.gr_sarea * self.detail.metal.close_node,
            'surf': self.detail.defect.surf_svol,
        }

        self.delta_time = self.exp_settings.time_step

    @property
    def conc_dis_plus(self):
        """
        Приток на дислокации
        """

        probability = 1 / (1 + 2 * b_factor(-self.detail.defect.dis_ener, self.temp))
        unit_volume = self.volumes['dis_plus']

        """
        n_vd = 3*pi*ro_d*a1^2*nu*n_v*tau*exp(-E_mv/(kT)) / (1+2*exp(-E_vd/(kT)))
        """

        # flow_plus = unit_volume * probability * self.conc_const * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp)
        flow_plus = unit_volume * probability * self.concentrations['vac'] * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp + 100)

        return flow_plus

    @property
    def conc_dis_minus(self):
        """
        Отток с дислокаций
        """

        probability = 1 / (1 + 0.5 * b_factor(-self.detail.defect.dis_ener, self.temp))
        unit_volume = self.volumes['dis_minus']

        """
        n_vd_ = pi*ro_d*a1^2*nu*n_vd*tau*exp(-E_mv/(kT)) / (1+0.5*exp(E_vd/(kT)))
        """
        flow_minus = unit_volume * probability * self.concentrations['dis'] * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp + 100)

        return flow_minus

    @property
    def conc_gr_plus(self):
        """
        Приток на зерна
        """

        probability = 1 / (1 + b_factor(-self.detail.defect.gr_ener, self.temp))
        unit_volume = self.volumes['gr']

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
        unit_volume = self.volumes['gr']

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
        unit_volume = self.volumes['tw']

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
        unit_volume = self.volumes['tw']

        """
        n_vg_ = 2*S_t*a1*nu*n_t*tau*exp(-E_mv/(kT)) / (1+exp(E_vg/(kT)))
        """
        flow_minus = unit_volume * probability * self.concentrations['tw'] * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp)

        return flow_minus

    @property
    def conc_surf_plus(self):
        """
        Приток на поверхность
        """

        probability = 1
        unit_volume = self.volumes['surf']

        """
        n_vg = Vs*nu*n_v*tau*exp(-E_mv/(kT)) / (1+exp(-E_vs/(kT)))
        """
        flow_plus = unit_volume * probability * self.concentrations['vac'] * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp)

        return flow_plus

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
        """
        Решение задачи Коши методом Эйлера
        """

        # Устанавливаем температуру равной начальной из БД
        self.temp = self.exp_settings.temp_start

        # Расчет шага температуры
        delta_T = self.exp_settings.time_step / self.exp_settings.warm_period
        print(f'delta_t {delta_T}')

        # Переменная номера шага для информативности
        step_count = 0

        # Выполняем расчет концентраций по шагам
        while self.temp <= self.exp_settings.temp_stop and self.concentrations['vac'] > 0:
            # Расчет концентрации на дислокациях
            dis_delta = self.conc_dis_plus - self.conc_dis_minus
            conc_dis_plus = self.conc_dis_plus
            conc_dis_minus = self.conc_dis_minus
            # b_factor_mig_minus = b_factor(-self.detail.defect.mig_ener, self.temp) * self.volumes['dis_minus'] * c.DEBYE * self.delta_time * self.concentrations["dis"]

            b_factor_mig_plus = b_factor(-self.detail.defect.mig_ener, self.temp)
            # b_factor_mig_plus = b_factor(-self.detail.defect.mig_ener, self.temp) * self.volumes[
            #     'dis_plus'] * c.DEBYE * self.delta_time * self.conc_const
            self.concentrations["dis"] += dis_delta
            prob_plus = 1 / (1 + 2 * b_factor(-self.detail.defect.dis_ener, self.temp))
            prob_minus = 1 / (1 + 0.5 * b_factor(-self.detail.defect.dis_ener, self.temp))


            # Расчет концентрации на зернах
            gr_delta = self.conc_gr_plus - self.conc_gr_minus
            self.concentrations["gr"] += gr_delta
            # Расчет концентрации на двойниках
            tw_delta = self.conc_tw_plus - self.conc_tw_minus
            self.concentrations["tw"] += tw_delta
            # Расчет концентрации на поверхности
            surf_delta = self.conc_surf_plus
            self.concentrations["surf"] += surf_delta
            # Расчет концентрации вакансий с учетом потоком на/с стоки
            vac_delta = dis_delta + gr_delta + tw_delta + surf_delta
            self.concentrations["vac"] -= vac_delta

            # print('==========================\n')

            con_sum = self.volumes['dis_plus'] * self.concentrations['dis'] + \
                self.volumes['gr'] * self.concentrations['gr'] + \
                self.volumes['tw'] * self.concentrations['tw'] + \
                self.volumes['surf'] * self.concentrations['surf']

            self.results.append(
                {
                    'T': self.temp,
                    'con_dis': [self.concentrations['dis'], dis_delta],
                    'con_dis_plus': conc_dis_plus,
                    'con_dis_minus': conc_dis_minus,
                    'con_gr': [self.concentrations['gr'], gr_delta],
                    'con_tw': [self.concentrations['tw'], tw_delta],
                    'con_surf': [self.concentrations['surf'], surf_delta],
                    'con_vac': [self.concentrations['vac'], -vac_delta],
                    'prob_plus': prob_plus,
                    'prob_minus': prob_minus,
                    'b_factor_mig_plus': b_factor_mig_plus,
                }
            )

            self.temp += delta_T
            step_count += 1

        return self.results


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vacancy.settings')

    defect = get_object_or_404(Defect, pk=1)

    metal = get_object_or_404(Metal, pk=1)

    settings = get_object_or_404(ExperimentSettings, pk=1)

    detail = Detail(metal=metal, defect=defect)

    experiment = Experiment(detail, settings)

    plot_values = experiment.start()
