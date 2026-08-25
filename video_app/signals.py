import django_rq
from django.db import transaction
from django.dispatch import receiver
from django.db.models.signals import post_save

from .models import Video
from .utils import convert_video


@receiver(post_save, sender=Video)
def start_converting_video(sender, instance, created, **kwargs):
    if not created:
        return
    def enqueue_conversion():
        django_rq.get_queue("default").enqueue(convert_video, instance.id)

    transaction.on_commit(enqueue_conversion)