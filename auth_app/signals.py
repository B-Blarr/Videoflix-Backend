from django.dispatch import receiver
from django.db.models.signals import post_save

from .models import User


@receiver(post_save, sender=User)
def send_activation_email(sender, instance, created, **kwargs):
    if not created or instance.is_active:
        return
    send_activation_email(instance)
