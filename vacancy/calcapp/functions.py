import numpy as n
import os

import numpy as np
from django.shortcuts import get_object_or_404
import django

from django.forms.models import model_to_dict

from calcapp.utils import export_results_to_xls, time_to_str

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


DELTA_TIME_MIN = 10

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

        # Устанавливаем температуру равной начальной из БД
        self.temp = self.exp_settings.temp_start

        self.rel_volume_clus = NV1C
        self.concentrations = {
            'dis': 0,
            'gr': 0,
            'tw': 0,
            'surf': 0,
            # 'vac': self.exp_settings.conc_vac_start,
            'vac': conc_rel_to_abs(self.exp_settings.conc_vac_start, self.detail.metal.grid_par),
        }

        self.conc_const = conc_rel_to_abs(self.exp_settings.conc_vac_start, self.detail.metal.grid_par)

        self.results = []

        self.volumes = {
            'dis_plus': 3 * n.pi * self.detail.metal.close_node ** 2,  # м2
            'dis_minus': n.pi * self.detail.metal.dis_dens * self.detail.metal.close_node ** 2,  # б/р
            'tw_plus': 2 * self.detail.metal.close_node,  # м
            'tw_minus': 2 * self.detail.metal.tw_sarea * self.detail.metal.close_node,  # б/р
            'gr_plus': 2 * self.detail.metal.close_node,  # м
            'gr_minus': 2 * self.detail.metal.gr_sarea * self.detail.metal.close_node,  # б/р
            'surf': self.detail.defect.surf_svol,  #
        }

        self.delta_time = self.exp_settings.time_step
        self.current_time = 0

    @property
    def conc_dis_plus(self):
        """
        Приток на дислокации
        """

        probability = 1 / (1 + 2 * b_factor(-self.detail.defect.dis_ener, self.temp))

        """
        n_vd = 3*pi*(1-4*a1*n_vd)*a1^2*n_v*tau*exp(-E_mv/(kT)) / (1+2*exp(-E_vd/(kT)))
        """

        # flow_plus = unit_volume * probability * self.conc_const * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp)
        flow_plus = 3 * np.pi * probability * (1 - 4 * self.detail.metal.close_node * conc_abs_to_rel(self.concentrations['dis'], self.detail.metal.grid_par)) * self.detail.metal.close_node ** 2 * self.concentrations['vac'] * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp) * c.DEBYE

        return flow_plus

    @property
    def conc_dis_minus(self):
        """
        Отток с дислокаций
        """

        probability = 1 / (1 + 0.5 * b_factor(self.detail.defect.dis_ener, self.temp))

        """
        n_vd_ = n_vd*tau*exp(-E_mv/(kT)) / (1+0.5*exp(E_vd/(kT)))
        """
        flow_minus = probability * self.concentrations['dis'] * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp) * c.DEBYE

        return flow_minus

    @property
    def dis_matrix_delta(self):
        """
        Вклад дислокаций в изменение вакансий в матрице
        """

        plus = self.conc_dis_minus
        # minus_ = self.conc_dis_plus
        minus = 3 * np.pi * self.detail.metal.close_node ** 2 * self.concentrations['vac'] * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp) / (1 + 2 * b_factor(-self.detail.defect.dis_ener, self.temp)) * c.DEBYE
        # spam = (1 - 3 * self.detail.metal.close_node * self.concentrations['dis'])
        """
        ro_d*n_vd*tau*exp(-E_mv/(kT)) / (1+0.5*exp(E_vd/(kT))) - 3*pi*ro_d*a1^2*n_v*tau*exp(-E_mv/(kT)) / (1+2*exp(-E_vd/(kT)))
        """
        dis_matrix_delta = self.detail.metal.dis_dens * (plus - minus)

        return dis_matrix_delta

    @property
    def conc_gr_plus(self):
        """
        Приток на зерна
        """

        probability = 1 / (1 + b_factor(-self.detail.defect.gr_ener, self.temp))

        """
        n_vg = 2*a1*(1-16*a1^2*n_vg)*n_v*tau*exp(-E_mv/(kT)) / (1+exp(-E_vg/(kT)))
        """
        flow_plus = 2 * self.detail.metal.close_node ** 2 * (1 - 16 * self.detail.metal.close_node ** 2 * conc_abs_to_rel(self.concentrations['gr'], self.detail.metal.grid_par)) * probability * self.concentrations['vac'] * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp) * c.DEBYE

        return flow_plus

    @property
    def conc_gr_minus(self):
        """
        Отток с зерен
        """

        probability = 1 / (1 + b_factor(self.detail.defect.gr_ener, self.temp))

        """
        n_vg_ = n_g*tau*exp(-E_mv/(kT)) / (1+exp(E_vg/(kT)))
        """
        flow_minus = probability * self.concentrations['gr'] * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp) * c.DEBYE

        return flow_minus

    @property
    def gr_matrix_delta(self):
        """
        Вклад дислокаций в изменение вакансий в матрице
        """

        plus = self.conc_gr_minus
        minus = 2 * self.detail.metal.close_node ** 2 * self.concentrations['vac'] * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp) / (1 + b_factor(self.detail.defect.gr_ener, self.temp)) * c.DEBYE

        """
        
        """
        gr_matrix_delta = self.detail.metal.gr_sarea * (plus - minus)

        return gr_matrix_delta

    @property
    def conc_tw_plus(self):
        """
        Приток на двойники
        """

        probability = 1 / (1 + b_factor(-self.detail.defect.tw_ener, self.temp))

        """
        
        """
        flow_plus = 2 * self.detail.metal.close_node ** 2 * (1 - 16 * self.detail.metal.close_node ** 2 * conc_abs_to_rel(self.concentrations['tw'], self.detail.metal.grid_par)) * probability * self.concentrations['vac'] * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp) * c.DEBYE

        return flow_plus

    @property
    def conc_tw_minus(self):
        """
        Отток с двойников
        """

        probability = 1 / (1 + b_factor(self.detail.defect.tw_ener, self.temp))

        """
        
        """
        flow_minus = probability * self.concentrations['tw'] * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp) * c.DEBYE

        return flow_minus

    @property
    def tw_matrix_delta(self):
        """
        Вклад дислокаций в изменение вакансий в матрице
        """

        plus = self.conc_gr_minus
        minus = 2 * self.detail.metal.close_node ** 2 * self.concentrations['vac'] * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp) / (1 + b_factor(self.detail.defect.gr_ener, self.temp)) * c.DEBYE

        """
        ro_d*n_vd*tau*exp(-E_mv/(kT)) / (1+0.5*exp(E_vd/(kT))) - 3*pi*ro_d*a1^2*n_v*tau*exp(-E_mv/(kT)) / (1+2*exp(-E_vd/(kT)))
        """
        tw_matrix_delta = self.detail.metal.tw_sarea * (plus - minus)

        return tw_matrix_delta

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
        # flow_plus = unit_volume * probability * self.concentrations['vac'] * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp)
        flow_plus = 0 * self.concentrations['vac'] * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp) * self.detail.metal.close_node

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

        # Расчет шага температуры
        delta_T = self.delta_time / self.exp_settings.warm_period
        self.temp += delta_T / 2

        # Переменная номера шага для информативности
        _step_count = 0

        is_dis_grow = True
        is_gr_grow = True
        is_tw_grow = True
        is_dis_grow_again = False
        is_gr_grow_again = False
        is_tw_grow_again = False

        # Выполняем расчет концентраций по шагам
        while self.current_time <= self.exp_settings.time_stop:

            # Расчет дельты концентрации на дислокациях
            conc_dis_plus = self.conc_dis_plus
            conc_dis_minus = self.conc_dis_minus
            dis_matrix_delta = self.dis_matrix_delta

            if conc_dis_plus < conc_dis_minus:
                is_dis_grow = False

            if not is_dis_grow:
                if conc_dis_plus > conc_dis_minus:
                    is_dis_grow_again = True

         #   if is_dis_grow_again or (self.concentrations["dis"] + conc_dis_plus - conc_dis_minus < 0):
          #          # and self.delta_time > DELTA_TIME_MIN:
           #     conc_dis_plus = conc_dis_minus
           #     dis_matrix_delta = 0
         #       is_dis_grow_again = False

                # if self.temp < self.exp_settings.temp_stop:
                #     self.temp -= delta_T
                # self.current_time -= self.delta_time
                #
                # self.delta_time /= 2
                #
                # self.current_time += self.delta_time
                # delta_T = self.delta_time / self.exp_settings.warm_period
                # if self.temp < self.exp_settings.temp_stop:
                #     self.temp += delta_T
                # is_dis_grow_again = False
                # continue

            # Расчет дельты концентрации на границах зерен
            conc_gr_plus = self.conc_gr_plus
            conc_gr_minus = self.conc_gr_minus
            gr_matrix_delta = self.gr_matrix_delta

            if conc_gr_plus < conc_gr_minus:
                is_gr_grow = False

            if not is_gr_grow:
                if conc_gr_plus > conc_gr_minus:
                    is_gr_grow_again = True

            if is_gr_grow_again or (self.concentrations["gr"] + conc_gr_plus - conc_gr_minus < 0):
                conc_gr_plus = conc_gr_minus
                gr_matrix_delta = 0
                is_gr_grow_again = False

            # Расчет дельты концентрации на двойниках
            conc_tw_plus = self.conc_tw_plus
            conc_tw_minus = self.conc_tw_minus
            tw_matrix_delta = self.tw_matrix_delta

            if conc_tw_plus < conc_tw_minus:
                is_tw_grow = False

            if not is_tw_grow:
                if conc_tw_plus > conc_tw_minus:
                    is_tw_grow_again = True

            if is_tw_grow_again or (self.concentrations["tw"] + conc_tw_plus - conc_tw_minus < 0):
                conc_tw_plus = conc_tw_minus
                tw_matrix_delta = 0
                is_tw_grow_again = False

            # if self.concentrations["dis"] < conc_dis_minus - conc_dis_plus and self.delta_time > DELTA_TIME_MIN:
            #     if self.temp < self.exp_settings.temp_stop:
            #             self.temp -= delta_T
            #     self.current_time -= self.delta_time
            #
            #     self.delta_time /= 2
            #
            #     self.current_time += self.delta_time
            #     delta_T = self.delta_time / self.exp_settings.warm_period
            #     if self.temp < self.exp_settings.temp_stop:
            #         self.temp += delta_T
            #     continue

            delta_vac = {'dis': conc_dis_plus - conc_dis_minus}

            # Расчет дельты концентрации на зернах
            delta_vac['gr'] = conc_gr_plus - conc_gr_minus

            # Расчет дельты концентрации на двойниках
            delta_vac['tw'] = conc_tw_plus - conc_tw_minus

            # Расчет дельты концентрации на поверхности
            delta_vac['surf'] = self.conc_surf_plus

            # Расчет дельты концентрации вакансий с учетом потоком на/с стоки
            # delta_vac["vac"] = self.dis_matrix_delta + self.gr_matrix_delta + self.tw_matrix_delta - delta_vac['surf']
            delta_vac["vac"] = dis_matrix_delta + gr_matrix_delta + tw_matrix_delta - delta_vac['surf']


            # Расчет концентраций
            for stock in ("dis", "gr", "tw", "surf", "vac"):
            # for stock in ("dis", "surf", "vac"):
                self.concentrations[stock] += delta_vac[stock]

            # Расчет вероятности дислокаций (вспомогательно)
            prob_plus = 1 / (1 + 2 * b_factor(-self.detail.defect.dis_ener, self.temp))
            prob_minus = 1 / (1 + 0.5 * b_factor(self.detail.defect.dis_ener, self.temp))

            self.results.append(
                {
                    'time': round(self.current_time / 60),
                    'time_range': time_to_str(int(self.current_time), int(self.delta_time)),
                    'T': self.temp,
                    'con_dis': [self.concentrations['dis'], delta_vac["dis"]],
                    'con_dis_plus': conc_dis_plus,
                    'con_dis_minus': conc_dis_minus,
                    'clean_delta': delta_vac["dis"] / b_factor(-self.detail.defect.mig_ener, self.temp) / c.DEBYE,
                    'con_gr': [self.concentrations['gr'], delta_vac["gr"]],
                    'con_tw': [self.concentrations['tw'], delta_vac["tw"]],
                    'con_surf': [self.concentrations['surf'], delta_vac["surf"]],
                    'con_vac': [self.concentrations['vac'], delta_vac["vac"]],
                    'prob_plus': prob_plus,
                    'prob_minus': prob_minus,
                    # 'b_factor': b_factor(-self.detail.defect.mig_ener, self.temp),
                }
            )

            if self.temp < self.exp_settings.temp_stop:
                self.temp += delta_T
            _step_count += 1
            self.current_time += self.delta_time

        return self.results


if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vacancy.settings')

    defect = get_object_or_404(Defect, pk=1)

    metal = get_object_or_404(Metal, pk=1)

    settings = get_object_or_404(ExperimentSettings, pk=1)

    detail = Detail(metal=metal, defect=defect)

    experiment = Experiment(detail, settings)

    plot_values = experiment.start()
