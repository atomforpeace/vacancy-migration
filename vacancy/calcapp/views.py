from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView

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
            'dis_svol',
            'gr_svol',
            'tw_svol',
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
        ):
            set_dict[attr] = float(post_data.get(attr, "0"))

        metal = Metal(**metal_dict)
        defect = Defect(**defect_dict)
        settings = ExperimentSettings(**set_dict)

        detail = Detail(metal, defect)
        experiment = Experiment(detail, settings)

        results, plot = experiment.start()

        plot_x = [x[0] for x in plot]
        plot_y = [y[1] for y in plot]

        trace = go.Scatter(x=plot_x, y=plot_y)
        layout = go.Layout(title="Результат", xaxis={'title': 'T'}, yaxis={'title': 'Dvt'})
        data = go.Data([trace])
        figure = go.Figure()
        figure.add_trace(go.Line(x=plot_x, y=plot_y))

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

        trace = go.Scatter(x=plot_x, y=plot_y)
        layout = go.Layout(title="Результат", xaxis={'title': 'T'}, yaxis={'title': 'Dvt'})
        data = go.Data([trace])
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
