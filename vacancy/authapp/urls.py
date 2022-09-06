from django.urls import path

from authapp.views import SiteLoginView, SiteLogoutView, SiteRegisterView


urlpatterns = [
    path("login/", SiteLoginView.as_view(), name="login"),
    path("logout/", SiteLogoutView.as_view(), name="logout"),
    path("register/", SiteRegisterView.as_view(), name="register"),
]
