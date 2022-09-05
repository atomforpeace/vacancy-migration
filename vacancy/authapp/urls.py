from django.urls import path

from authapp.views import SiteLoginView


urlpatterns = [
    path("login/", SiteLoginView.as_view(), name="login"),
]
