from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

import plotly.graph_objects as go

from calcapp.functions import Detail, Experiment
from calcapp.models import Metal, Defect, ExperimentSettings
from calcapp.utils import filter_results


PLOT_HEIGHT = 400
PLOT_WIDTH = 1200


class CalcView(View):
    template_name = 'calcapp/main.html'

    def post(self, request, *args, **kwargs):
        post_data = request.POST

        metal_dict = {}

        for attr in (
            'gr_sarea',
            'tw_sarea',
            'dis_dens',
            'grid_par',
            'close_node',
        ):
            metal_dict[attr] = float(post_data.get(attr, "0"))

        defect_dict = {}

        for attr in (
            'form_ener',
            'mig_ener',
            'dis_ener',
            'gr_ener',
            'tw_ener',
            'clus_init_diam',
            'clus_init_count',
            'recomb_rad',
            'surf_svol',
        ):
            defect_dict[attr] = float(post_data.get(attr, "0"))

        set_dict = {}

        for attr in (
            'warm_period',
            'temp_start',
            'temp_stop',
            'time_step',
            'time_stop',
            'conc_vac_start',
        ):
            set_dict[attr] = float(post_data.get(attr, "0"))

        metal = Metal(**metal_dict)
        defect = Defect(**defect_dict)
        settings = ExperimentSettings(**set_dict)

        detail = Detail(metal, defect)
        experiment = Experiment(detail, settings)

        results = experiment.start()

        plot_x = [item['time'] for item in results]
        plot_T = [item['T'] for item in results]
        plot_dis = [item['con_dis'][0] for item in results]
        plot_dis_plus = [item['con_dis_plus'] for item in results]
        plot_dis_minus = [item['con_dis_minus'] for item in results]
        plot_dis_delta = [item['con_dis_plus'] - item['con_dis_minus'] for item in results]
        plot_gr = [item['con_gr'][0] for item in results]
        plot_tw = [item['con_tw'][0] for item in results]
        plot_surf = [item['con_surf'][0] for item in results]
        plot_vac = [item['con_vac'][0] for item in results]
        plot_prob_plus = [item['prob_plus'] for item in results]
        plot_prob_minus = [item['prob_minus'] for item in results]
        plot_b_factor_mig_plus = [item['b_factor_mig_plus'] for item in results]

        figure_temp = go.Figure()
        figure_temp.add_trace(go.Line(x=plot_x, y=plot_T, name="Температура"))
        figure_temp.update_layout(
            title="Рост температуры",
            height=PLOT_HEIGHT,
            width=PLOT_WIDTH,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="left",
                x=0.01
            )
        )
        figure_temp.update_xaxes(title="Время, мин")

        figure_vac = go.Figure()
        figure_vac.add_trace(go.Line(x=plot_x, y=plot_dis, name="Дислокации"))
        figure_vac.add_trace(go.Line(x=plot_x, y=plot_gr, name="Зерна"))
        figure_vac.add_trace(go.Line(x=plot_x, y=plot_tw, name="Двойники"))
        figure_vac.add_trace(go.Line(x=plot_x, y=plot_surf, name="Поверхность"))
        figure_vac.add_trace(go.Line(x=plot_x, y=plot_vac, name="В матрице"))
        figure_vac.update_layout(
            title="Вакансии",
            height=PLOT_HEIGHT,
            width=PLOT_WIDTH,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.4,
                xanchor="left",
                x=0.01
            )
        )
        figure_vac.update_xaxes(title="Время, мин")

        figure_flows = go.Figure()
        figure_flows.add_trace(go.Line(x=plot_x, y=plot_dis_plus, name="На дислокации"))
        figure_flows.add_trace(go.Line(x=plot_x, y=plot_dis_minus, name="С дислокаций"))
        figure_flows.update_yaxes(exponentformat="E")
        figure_flows.update_layout(
            title="Потоки на/с дислокаций",
            height=PLOT_HEIGHT,
            width=PLOT_WIDTH,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="left",
                x=0.01
            )
        )
        figure_flows.update_xaxes(title="Время, мин")

        figure_flows_delta = go.Figure()
        figure_flows_delta.add_trace(go.Line(x=plot_x, y=plot_dis_delta, name="Дельта на дислокациях"))
        figure_flows_delta.update_layout(
            title="Дельта потоков на дислокациях",
            height=PLOT_HEIGHT,
            width=PLOT_WIDTH,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.1,
                xanchor="left",
                x=0.01
            )
        )
        figure_flows_delta.update_xaxes(title="Время, мин")

        figure_probability = go.Figure()
        figure_probability.add_trace(go.Line(x=plot_x, y=plot_prob_plus, name="Вероятность притока на дислокации"))
        figure_probability.add_trace(go.Line(x=plot_x, y=plot_prob_minus, name="Вероятность оттока с дислокаций"))
        figure_probability.update_layout(
            title="Вероятности",
            height=PLOT_HEIGHT,
            width=PLOT_WIDTH,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="left",
                x=0.01
            ),
        )
        figure_probability.update_xaxes(title="Время, мин")

        figure_b_factor_mig = go.Figure()
        figure_b_factor_mig.add_trace(go.Line(x=plot_x, y=plot_b_factor_mig_plus, name="exp(-Emv/kT)"))
        figure_b_factor_mig.update_yaxes(exponentformat="E")
        figure_b_factor_mig.update_layout(
            title="exp(-Emv/kT)",
            height=PLOT_HEIGHT,
            width=PLOT_WIDTH,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.1,
                xanchor="left",
                x=0.01
            ),
        )
        figure_b_factor_mig.update_xaxes(title="Время, мин")

        # figure_b_factor_prob = go.Figure()
        # figure_b_factor_prob.add_trace(go.Line(x=plot_x, y=plot_b_factor_prob_plus, name="Множитель+"))
        # figure_b_factor_prob.add_trace(go.Line(x=plot_x, y=plot_b_factor_prob_minus, name="Множитель-"))
        # figure_b_factor_prob.update_layout(
        #     title="Множитель без концентраций",
        #     height=PLOT_HEIGHT,
        #     width=PLOT_WIDTH,
        #     legend=dict(
        #         orientation="h",
        #         yanchor="bottom",
        #         y=-0.1,
        #         xanchor="left",
        #         x=0.01
        #     ),
        # )

        results = filter_results(results, excluded=['prob_plus', 'prob_minus'])

        context = {
            'results': results,
            'figure_temp': figure_temp.to_html(),
            'figure_vac': figure_vac.to_html(),
            'figure_flows': figure_flows.to_html(),
            'figure_flows_delta': figure_flows_delta.to_html(),
            'figure_probability': figure_probability.to_html(),
            'figure_b_factor_mig': figure_b_factor_mig.to_html(),
            # 'figure_b_factor_prob': figure_b_factor_prob.to_html(),
        }
        # print(results)

        return render(request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        detail = Detail()
        experiment = Experiment(detail)

        results, plot = experiment.start()

        plot_x = [x[0] for x in plot]
        plot_y = [y[1] for y in plot]

        # trace = go.Scatter(x=plot_x, y=plot_y)
        # layout = go.Layout(title="Результат", xaxis={'title': 'T'}, yaxis={'title': 'Dvt'})
        # data = go.Data([trace])
        figure = go.Figure()
        figure.add_trace(go.Line(x=plot_x, y=plot_y))

        context = {
            'results': results,
            'figure': figure.to_html(),
        }

        return render(request, self.template_name, context)


def download_xlsx(request, path):
    with open(f'files/{path}', 'rb') as f:
        response = HttpResponse(f.read(), content_type="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename=results.xlsx'
        return response
