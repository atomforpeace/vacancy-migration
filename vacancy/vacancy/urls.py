from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include
from django.views.generic import TemplateView

from authapp.forms import AdminLoginForm

admin.autodiscover()
admin.site.login_form = AdminLoginForm
admin.site.login_template = 'authapp/login.html'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='mainapp/index.html'), name='index'),

    path("auth/", include(("authapp.urls", "authapp"), namespace="auth")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
