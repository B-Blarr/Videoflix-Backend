import django_rq
from django.conf import settings
from django.db import transaction
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

from .models import Video
from .utils import convert_video, remove_video_files


@receiver(post_save, sender=Video)
def start_converting_video(sender, instance, created, **kwargs):
    if not created:
        return
    def enqueue_conversion():
        django_rq.get_queue('low').enqueue(
            convert_video, instance.id,
            job_timeout=settings.HLS_JOB_TIMEOUT)

    transaction.on_commit(enqueue_conversion)


@receiver(post_delete, sender=Video)
def delete_video_files(sender, instance, **kwargs):
    remove_video_files(instance)