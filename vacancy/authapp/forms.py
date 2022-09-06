from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox
from django.contrib.auth.forms import AuthenticationForm
from django.forms import forms

from authapp.models import SiteUser


class SiteUserLoginForm(AuthenticationForm):
    """
    Форма аутентификации
    """
    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox, label="Подтвердите, что вы не робот!"
    )

    class Meta:
        model = SiteUser

    def __init__(self, *args, **kwargs):
        super(SiteUserLoginForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == 'password':
                field.widget.attrs["class"] = "form-control"
            else:
                field.widget.attrs["class"] = "form-control mb-2"
            field.help_text = ""


class AdminLoginForm(AuthenticationForm):
    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox, label="Подтвердите что вы не робот!"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"
            field.help_text = ""
