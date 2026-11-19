from django.conf import settings
from django.db import models

from .validators import avatar_upload_to, avatar_validators


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Пользователь",
    )
    avatar = models.ImageField(
        "Аватар", upload_to=avatar_upload_to, blank=True, validators=avatar_validators
    )

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return self.user.username
