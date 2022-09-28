from django.contrib import admin

from calcapp.models import (
    ExperimentSettings,
    Experiment,
    Defect,
    Metal,
)

admin.site.register(ExperimentSettings)
admin.site.register(Experiment)
admin.site.register(Defect)
admin.site.register(Metal)
