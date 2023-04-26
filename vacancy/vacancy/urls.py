from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include
from django.views.generic import TemplateView

from authapp.forms import AdminLoginForm
from calcapp.utils import export_results_to_xls
from calcapp.views import CalcView, download_xlsx
from mainapp.views import SetExperimentData, update_form

admin.autodiscover()
admin.site.login_form = AdminLoginForm
admin.site.login_template = 'authapp/login.html'

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('', TemplateView.as_view(template_name='mainapp/index.html'), name='index'),
    path('', SetExperimentData.as_view(), name='index'),

    path("auth/", include(("authapp.urls", "authapp"), namespace="auth")),

    path('calc/', CalcView.as_view(), name='calc'),
    path('update/<int:pk>/', update_form, name='update'),
    path('download/<str:path>', download_xlsx, name='download-xlsx'),
    path('formulas/', TemplateView.as_view(template_name='mainapp/formulas.html'), name='formulas'),
    # path('api-auth/', include('rest_framework.urls'))

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
