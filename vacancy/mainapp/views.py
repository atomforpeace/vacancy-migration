from django.shortcuts import render, get_object_or_404
from django.views import View
from django.views.generic import DetailView, CreateView, FormView, TemplateView
from rest_framework.response import Response
from rest_framework.views import APIView

from calcapp.models import Metal, Defect, ExperimentSettings
from calcapp.serializers import MetalSerializer
from mainapp.forms import MetalUpdateForm, DefectUpdateForm, MultiFormsView, SettingsUpdateForm
from django.forms.models import model_to_dict


class ListMetalApi(APIView):
    def get(self, request, format=None):
        data = Metal.objects.all()
        serializer = MetalSerializer(data, many=True)

        return Response(serializer.data)


class SetExperimentData(MultiFormsView):
    form_classes = {
        'metal': MetalUpdateForm,
        'defect': DefectUpdateForm,
        'settings': SettingsUpdateForm,
    }
    template_name = "mainapp/index.html"

    def get_metal_initial(self):
        obj = get_object_or_404(Metal, pk=1)
        return model_to_dict(obj)

    def get_defect_initial(self):
        obj = get_object_or_404(Defect, pk=1)
        return model_to_dict(obj)

    def get_settings_initial(self):
        obj = get_object_or_404(ExperimentSettings, pk=1)
        return model_to_dict(obj)
