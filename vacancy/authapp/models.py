from django.contrib.auth.models import AbstractUser
from django.db import models


class SiteUser(AbstractUser):

    def __str__(self):
        return f'{self.last_name} {self.first_name[:1]}.'
