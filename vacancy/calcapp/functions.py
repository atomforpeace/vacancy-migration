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


# Если True, будет скорректирован расчет концентраций.
# Если False - обычный расчет.
CORRECT_COUNT = True

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
        return ener / self.defect.form_ener * 0.15 * self.metal.atomic_volume

    @property
    def volume_delta(self):
        """
        Изменение объема
        """
        return {
            'dis': self.vol_change(ener=self.defect.dis_ener),
            'gr': self.vol_change(ener=self.defect.gr_ener),
            'tw': self.vol_change(ener=self.defect.tw_ener),
            'surf': 0.85 * self.metal.atomic_volume,
        }

    @property
    def volume(self):
        return self.metal.grid_par ** 3 / 2


class Experiment:
    """
    Эксперимент
    """

    # ВСЕ ВИДЫ СТОКОВ
    TYPES = (
        "dis",
        "tw",
        "gr",
        "surf",
        "vac",
    )

    def __init__(self, detail, exp_settings):
        self.detail = detail
        self.exp_settings = exp_settings

        # Устанавливаем температуру равной начальной из БД
        self.temp = self.exp_settings.temp_start

        # Назначаем переменную для изменения размера
        self.delta_size = 0

        # Назначаем предел для дислокаций
        self.dis_limit = self.detail.metal.atomic_volume ** (-1 / 3)
        self.dis_layers = 0

        # Назначаем предел для поверхности
        self.surf_limit = self.detail.metal.atomic_volume ** (-2 / 3)
        self.surf_layers = 0

        # self.rel_volume_clus = NV1C
        self.concentrations = {
            'dis': 0,
            'gr': 0,
            'tw': 0,
            'surf': 0,
            # 'vac': self.exp_settings.conc_vac_start,
            'vac': conc_rel_to_abs(self.exp_settings.conc_vac_start, self.detail.metal.grid_par),
        }



        self.concentrations_delta = {
            "dis": 1,
            "gr": 1,
            "tw": 1,
        }

        self.concentrations_delta_prev = {
            "dis": 1,
            "gr": 1,
            "tw": 1,
        }

        self.conc_coef = {
            "dis": 1,
            "gr": 1,
            "tw": 1,
        }

        self.is_grow = {
            "dis": True,
            "gr": True,
            "tw": True,
        }

        self.is_fall_slow = {
            "dis": False,
            "gr": False,
            "tw": False,
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

    def func_conc(self, type_: str, temp: float, concentrations: dict):
        functions = {
            "dis": self.func_conc_dis(temp, concentrations),
            "tw": self.func_conc_tw(temp, concentrations),
            "gr": self.func_conc_gr(temp, concentrations),
            "surf": self.func_conc_surf(temp, concentrations),
            "vac": self.func_conc_vac(temp, concentrations),
        }

        if type_ in functions:
            return functions[type_]
        else:
            raise TypeError

    def func_conc_dis(self, temp, concentrations: dict):
        """
        Новая реализация расчетов (июнь 2023)
        Функция расчета концентрации на дислокации (без умножения на время)
        :param concentrations:
        :return:
        """
        probability = 1 / (1 + 2 * b_factor(-self.detail.defect.dis_ener, temp))
        conc_plus = 3 * np.pi * probability * (1 - 4 * self.detail.metal.close_node * concentrations["dis"]) * self.detail.metal.close_node ** 2 * \
            concentrations['vac'] * b_factor(-self.detail.defect.mig_ener, temp) * c.DEBYE

        probability = 1 / (1 + 0.5 * b_factor(self.detail.defect.dis_ener, temp))
        conc_minus = probability * concentrations["dis"] * b_factor(-self.detail.defect.mig_ener, temp) * c.DEBYE
        return conc_plus - conc_minus

    def func_conc_tw(self, temp, concentrations: dict):
        """
        Новая реализация расчетов (июнь 2023)
        Функция расчета концентрации на двойники (без умножения на время)
        :param concentrations:
        :return:
        """
        probability = 1 / (1 + b_factor(-self.detail.defect.tw_ener, temp))
        conc_plus = 2 * self.detail.metal.close_node ** 2 * (1 - 16 * self.detail.metal.close_node ** 2 * concentrations['tw']) * probability * \
                    concentrations['vac'] * b_factor(-self.detail.defect.mig_ener, temp) * c.DEBYE

        probability = 1 / (1 + b_factor(self.detail.defect.tw_ener, temp))
        conc_minus = probability * concentrations['tw'] * b_factor(-self.detail.defect.mig_ener, temp) * c.DEBYE

        return conc_plus - conc_minus

    def func_conc_gr(self, temp, concentrations: dict):
        """
        Новая реализация расчетов (июнь 2023)
        Функция расчета концентрации на зерна (без умножения на время)
        :param concentrations:
        :return:
        """

        probability = 1 / (1 + b_factor(-self.detail.defect.gr_ener, temp))
        conc_plus = 2 * self.detail.metal.close_node ** 2 * (1 - 16 * self.detail.metal.close_node ** 2 * concentrations['gr']) * \
                    probability * concentrations['vac'] * b_factor(-self.detail.defect.mig_ener, temp) * c.DEBYE

        probability = 1 / (1 + b_factor(self.detail.defect.gr_ener, temp))
        conc_minus = probability * concentrations['gr'] * b_factor(-self.detail.defect.mig_ener, temp) * c.DEBYE

        return conc_plus - conc_minus

    def func_conc_surf(self, temp, concentrations: dict):
        """
        Новая реализация расчетов (июнь 2023)
        Функция расчета концентрации на поверхность (без умножения на время)
        :param concentrations:
        :return:
        """

        flow_plus = 1080 * concentrations['vac'] * c.DEBYE * b_factor(-self.detail.defect.mig_ener, temp) * self.detail.metal.close_node

        return flow_plus

    def func_conc_vac(self, temp, concentrations: dict):
        """
        Новая реализация расчетов (июнь 2023)
        Функция расчета изменения концентраций в матрице за счет потока с дислокаций (без умножения на время)
        :param temp:
        :param concentrations:
        :return:
        """

        probability = 1 / (1 + 0.5 * b_factor(self.detail.defect.dis_ener, temp))
        dis_conc_plus = probability * concentrations['dis'] * b_factor(-self.detail.defect.mig_ener, temp) * c.DEBYE

        probability = 1 / (1 + 2 * b_factor(-self.detail.defect.dis_ener, temp))
        dis_conc_minus = probability * 3 * np.pi * self.detail.metal.close_node ** 2 * concentrations['vac'] * b_factor(-self.detail.defect.mig_ener, temp)

        probability = 1 / (1 + b_factor(self.detail.defect.tw_ener, temp))
        tw_conc_plus = probability * concentrations['tw'] * b_factor(-self.detail.defect.mig_ener, temp) * c.DEBYE

        probability = 1 / (1 + b_factor(-self.detail.defect.tw_ener, temp))
        tw_conc_minus = 2 * self.detail.metal.close_node ** 2 * probability * concentrations['vac'] * b_factor(-self.detail.defect.mig_ener, temp) * c.DEBYE

        probability = 1 / (1 + b_factor(self.detail.defect.gr_ener, temp))
        gr_conc_plus = probability * concentrations['gr'] * b_factor(-self.detail.defect.mig_ener, temp) * c.DEBYE

        probability = 1 / (1 + b_factor(-self.detail.defect.gr_ener, temp))
        gr_conc_minus = 2 * self.detail.metal.close_node ** 2 * probability * concentrations['vac'] * b_factor(-self.detail.defect.mig_ener, temp) * c.DEBYE

        flow_plus = 1080 * concentrations['vac'] * c.DEBYE * b_factor(-self.detail.defect.mig_ener,
                                                                      temp) * self.detail.metal.close_node
        print(self.detail.metal.dis_dens * (dis_conc_plus - dis_conc_minus) * 60 + \
        self.detail.metal.tw_sarea * (tw_conc_plus - tw_conc_minus) * 60 + \
        self.detail.metal.gr_sarea * (gr_conc_plus - gr_conc_minus) * 60 + \
        flow_plus * 60)

        return self.detail.metal.dis_dens * (dis_conc_plus - dis_conc_minus) + \
            self.detail.metal.tw_sarea * (tw_conc_plus - tw_conc_minus) + \
            self.detail.metal.gr_sarea * (gr_conc_plus - gr_conc_minus) - flow_plus


    def conc_dis(self, conc_tmp):
        probability = 1 / (1 + 2 * b_factor(-self.detail.defect.dis_ener, self.temp))
        conc_plus = 3 * np.pi * probability * (1 - 4 * self.detail.metal.close_node * conc_tmp) * self.detail.metal.close_node ** 2 * \
        self.concentrations['vac'] * b_factor(-self.detail.defect.mig_ener, self.temp) * c.DEBYE

        probability = 1 / (1 + 0.5 * b_factor(self.detail.defect.dis_ener, self.temp))

        conc_minus = probability * conc_tmp * b_factor(-self.detail.defect.mig_ener, self.temp) * c.DEBYE
        return (conc_plus - conc_minus) * self.delta_time

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
        flow_plus = 3 * np.pi * probability * (1 - 4 * self.detail.metal.close_node * self.concentrations['dis']) * self.detail.metal.close_node ** 2 * self.concentrations['vac'] * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp) * c.DEBYE

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
        flow_plus = 2 * self.detail.metal.close_node ** 2 * (1 - 16 * self.detail.metal.close_node ** 2 * self.concentrations['gr']) * probability * self.concentrations['vac'] * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp) * c.DEBYE

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
        flow_plus = 2 * self.detail.metal.close_node ** 2 * (1 - 16 * self.detail.metal.close_node ** 2 * self.concentrations['tw']) * probability * self.concentrations['vac'] * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp) * c.DEBYE

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
        flow_plus = 1080 * self.concentrations['vac'] * c.DEBYE * self.delta_time * b_factor(-self.detail.defect.mig_ener, self.temp) * self.detail.metal.close_node

        return flow_plus

    def correct_flow(self, type_):
        values = {
            "dis": [self.conc_dis_plus - self.conc_dis_minus, self.dis_matrix_delta],
            "gr": [self.conc_gr_plus - self.conc_gr_minus, self.gr_matrix_delta],
            "tw": [self.conc_tw_plus - self.conc_tw_minus, self.tw_matrix_delta],
        }

        delta, matrix_delta = values[type_]

        if self.concentrations[type_] + delta < 0:
            delta = 0
            matrix_delta = 0
        else:
            if delta < 0:
                self.is_grow[type_] = False

            if not self.is_grow[type_]:
                self.conc_coef[type_] = self.concentrations_delta[type_] / self.concentrations_delta_prev[type_]

                if self.concentrations_delta[type_] > self.concentrations_delta_prev[type_]:
                    self.is_fall_slow[type_] = True

                if self.is_fall_slow[type_]:
                    if delta > self.concentrations_delta[type_]:
                        matrix_delta = matrix_delta * self.concentrations_delta[type_] * self.conc_coef[
                            type_] / delta
                        delta = self.concentrations_delta[type_] * self.conc_coef[type_]

                if self.concentrations[type_] + delta < 0:
                    delta = 0
                    matrix_delta = 0

            self.concentrations_delta_prev[type_] = self.concentrations_delta[type_]
            if delta != 0:
                self.concentrations_delta[type_] = delta

        return delta, matrix_delta

    def count_euler(self, temp, delta_T, concentrations):
        """
        Основной расчет концентраций
        :param concentrations:
        :param delta_time:
        :param delta_T:
        :return:
        """

        # Вспомогательные переменные
        concentrations_forecast = {"vac": concentrations["vac"]}
        delta_stock = {}

        # РАСЧЕТ ПРОМЕЖУТОЧНЫХ ЗНАЧЕНИЙ
        for stock in ("dis", "gr", "tw", "surf"):
            delta_stock[stock] = self.func_conc(type_=stock, temp=temp,
                                                concentrations=concentrations) * self.delta_time
            concentrations_forecast[stock] = concentrations[stock] + delta_stock[stock] / 2


        # РАСЧЕТ ЗНАЧЕНИЙ КОНЦЕНТРАЦИИ
        for stock in ("dis", "gr", "tw", "surf"):
            delta_stock[stock] = self.func_conc(type_=stock, temp=temp + delta_T / 2,
                                                concentrations=concentrations_forecast) * self.delta_time
            concentrations[stock] += delta_stock[stock]

        delta_stock["vac"] = self.func_conc("vac", temp=temp, concentrations=concentrations) * self.delta_time
        concentrations["vac"] += delta_stock["vac"]

        # print(delta_stock["surf"], delta_stock["vac"])

        return delta_stock, concentrations

    def count_runge_kutt(self, temp, delta_T, concentrations):
        """
        Основной расчет концентраций
        :param concentrations:
        :param delta_time:
        :param delta_T:
        :return:
        """

        # Вспомогательные переменные
        concentrations_forecast = {"vac": concentrations["vac"]}
        delta_stock = {}

        # РАСЧЕТ ПРОМЕЖУТОЧНЫХ ЗНАЧЕНИЙ
        for stock in ("dis", "gr", "tw", "surf"):
            delta_stock[stock] = self.func_conc(type_=stock, temp=temp,
                                                concentrations=concentrations) * self.delta_time
            concentrations_forecast[stock] = concentrations[stock] + delta_stock[stock] / 2


        # РАСЧЕТ ЗНАЧЕНИЙ КОНЦЕНТРАЦИИ
        for stock in ("dis", "gr", "tw", "surf"):
            delta_stock[stock] = self.func_conc(type_=stock, temp=temp + delta_T / 2,
                                                concentrations=concentrations_forecast) * self.delta_time
            concentrations[stock] += delta_stock[stock]

        delta_stock["vac"] = self.func_conc("vac", temp=temp, concentrations=concentrations) * self.delta_time
        concentrations["vac"] += delta_stock["vac"]

        # print(delta_stock["surf"], delta_stock["vac"])

        return delta_stock, concentrations

    def start(self):
        """
        Решение задачи Коши усовершенствованным методом Эйлера
        """

        # Расчет шага температуры
        delta_T = self.delta_time / self.exp_settings.warm_period

        # Выполняем расчет концентраций по шагам
        while self.current_time <= self.exp_settings.time_stop:

            if CORRECT_COUNT:
                delta_stock, concentrations = self.count_euler(self.temp, delta_T, self.concentrations)
                for stock in ("dis", "gr", "tw"):
                    if self.concentrations[stock] + delta_stock[stock] < 0:
                        delta_stock[stock] = 0
                    else:
                        # Растет ли концентрация на стоке?
                        if delta_stock[stock] < 0:
                            self.is_grow[stock] = False

                        # Если концентрация на стоке падает, расчитываем коэффициент падения
                        if not self.is_grow[stock]:
                            self.conc_coef[stock] = self.concentrations_delta[stock] / self.concentrations_delta_prev[stock]

                            # Если дельта уменьшения до этого уменьшалась по модулю
                            if abs(self.concentrations_delta[stock]) < abs(self.concentrations_delta_prev[stock]):
                                self.is_fall_slow[stock] = True

                            # Отлавливаем момент, когда концентрации снова увеличиваются
                            if self.is_fall_slow[stock]:
                                # Если снова растет (хотя не должен)
                                if delta_stock[stock] > self.concentrations_delta[stock]:
                                    # matrix_delta = matrix_delta * self.concentrations_delta[stock] * self.conc_coef[
                                    #     stock] / delta
                                    delta_stock[stock] = self.concentrations_delta[stock] * self.conc_coef[stock]
                                    self.concentrations[stock] += delta_stock[stock]
                                    # delta_stock_, concentrations_ = self.count_conc(self.temp + delta_T, delta_T, concentrations)
                                    # delta_stock[stock] = (delta_stock_[stock] + delta_stock[stock]) / 2
                                    # self.concentrations[stock] = (concentrations_[stock] + concentrations[stock]) / 2

                            # if self.concentrations[stock] + delta < 0:
                            #     delta = 0
                            #     matrix_delta = 0

                        self.concentrations_delta_prev[stock] = self.concentrations_delta[stock]
                        if delta_stock[stock] != 0:
                            self.concentrations_delta[stock] = delta_stock[stock]
            else:
                delta_stock, self.concentrations = self.count_euler(delta_T, self.concentrations)

            self.results.append(
                {
                    'time': round(self.current_time / 60),
                    'time_range': time_to_str(int(self.current_time), int(self.delta_time)),
                    'T': self.temp,
                    'con_dis': [self.concentrations['dis'], delta_stock["dis"]],
                    # 'clean_delta': delta_vac["dis"] / b_factor(-self.detail.defect.mig_ener, self.temp) / c.DEBYE,
                    'con_gr': [self.concentrations['gr'], delta_stock["gr"]],
                    'con_tw': [self.concentrations['tw'], delta_stock["tw"]],
                    'con_surf': [self.concentrations['surf'], delta_stock["surf"]],
                    'con_vac': [self.concentrations['vac'], delta_stock["vac"]],
                    'length': self.delta_size,
                }
            )

            if self.temp < self.exp_settings.temp_stop:
                self.temp += delta_T

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
