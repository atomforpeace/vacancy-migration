from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from authapp.forms import SiteUserLoginForm, SiteUserRegistrationForm
from authapp.models import SiteUser


class SiteLoginView(LoginView):
    template_name = 'authapp/login.html'
    form_class = SiteUserLoginForm
    success_url = reverse_lazy("index")
    redirect_authenticated_user = True


class SiteLogoutView(LogoutView):
    """
    Контроллер выхода из системы
    """
    model = SiteUser
    login_url = reverse_lazy("auth:login")
    next_page = reverse_lazy("index")


class SiteRegisterView(CreateView):
    """
    Контроллер регистрации
    """
    Model = SiteUser
    form_class = SiteUserRegistrationForm
    template_name = "authapp/registration.html"
    success_url = reverse_lazy("index")

    def dispatch(self, request, *args, **kwargs):
        if not self.request.user.is_staff:
            return redirect("/")
        return super().dispatch(request, *args, **kwargs)
