from django.contrib.auth.views import LoginView
from django.shortcuts import render

from authapp.forms import SiteUserLoginForm


class SiteLoginView(LoginView):
    template_name = 'authapp/login.html'
    form_class = SiteUserLoginForm
