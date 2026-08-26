from django.dispatch import receiver
from django.db import transaction
from django.db.models.signals import post_save
import django_rq

from .models import User
from .utils import send_activation_email


@receiver(post_save, sender=User)
def send_activation_email_on_create(sender, instance, created, **kwargs):
    if not created or instance.is_active:
        return
    def enqueue_activation_mail():
        django_rq.get_queue("high").enqueue(send_activation_email, instance.id)
    transaction.on_commit(enqueue_activation_mail)

