from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

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


def update_form(request, pk):
    metal = get_object_or_404(Metal, pk=pk)
    defect = get_object_or_404(Defect, pk=pk)
    settings = get_object_or_404(ExperimentSettings, pk=pk)
    metal_form = MetalUpdateForm(request.POST, instance=metal)
    defect_form = DefectUpdateForm(request.POST, instance=defect)
    settings_form = SettingsUpdateForm(request.POST, instance=settings)
    if metal_form.is_valid() and defect_form.is_valid() and settings_form.is_valid():
        metal_form.save()
        defect_form.save()
        settings_form.save()
    return HttpResponseRedirect('/')
