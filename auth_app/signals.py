from .models import User
from django.dispatch import receiver
from django.db.models.signals import post_save


@receiver(post_save, sender=User)
def send_activation_email(sender, instance, created, **kwargs):
    pass