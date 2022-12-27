from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

import plotly.graph_objects as go

from calcapp.functions import Detail, Experiment
from calcapp.models import Metal, Defect, ExperimentSettings


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
        ):
            defect_dict[attr] = float(post_data.get(attr, "0"))

        set_dict = {}

        for attr in (
            'warm_period',
            'temp_start',
            'temp_stop',
            'time_step',
            'conc_vac_start',
        ):
            set_dict[attr] = float(post_data.get(attr, "0"))

        metal = Metal(**metal_dict)
        defect = Defect(**defect_dict)
        settings = ExperimentSettings(**set_dict)

        detail = Detail(metal, defect)
        experiment = Experiment(detail, settings)

        results = experiment.start()

        plot_x = [item['T'] for item in results]
        plot_dis = [item['con_dis'][0] for item in results]
        plot_gr = [item['con_gr'][0] for item in results]
        plot_tw = [item['con_tw'][0] for item in results]
        plot_surf = [item['con_surf'][0] for item in results]
        plot_vac = [item['con_vac'][0] for item in results]

        # trace_dis = go.Scatter(x=plot_x, y=plot_dis)
        # trace_gr = go.Scatter(x=plot_x, y=plot_gr)
        # trace_tw = go.Scatter(x=plot_x, y=plot_tw)
        # trace_vac = go.Scatter(x=plot_x, y=plot_vac)
        # layout = go.Layout(title="Результат", xaxis={'title': 'T'}, yaxis={'title': 'Dvt'})
        # data = go.Data([trace_dis, trace_gr])
        figure = go.Figure()
        figure.add_trace(go.Line(x=plot_x, y=plot_dis, name="Дислокации"))
        figure.add_trace(go.Line(x=plot_x, y=plot_gr, name="Зерна"))
        figure.add_trace(go.Line(x=plot_x, y=plot_tw, name="Двойники"))
        figure.add_trace(go.Line(x=plot_x, y=plot_surf, name="Поверхность"))
        figure.add_trace(go.Line(x=plot_x, y=plot_vac, name="В матрице"))

        context = {
            'results': results,
            'figure': figure.to_html(),
        }

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
