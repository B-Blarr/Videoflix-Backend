"""Custom user model for Videoflix, logging in with the email."""

from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """User that logs in by email; username stays for createsuperuser."""

    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        """Return the email, which is what identifies the user."""

        return self.email

