import django_rq
from django.conf import settings
from django.db import transaction
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete, pre_save

from .models import Video
from .utils import convert_video, drop_replaced_source, remove_video_files


@receiver(pre_save, sender=Video)
def remember_stored_file(sender, instance, **kwargs):
    """Remember the stored file name so post_save can spot a replacement."""
    instance._stored_file = None
    if instance.pk:
        instance._stored_file = Video.objects.filter(
            pk=instance.pk).values_list('video_file', flat=True).first()


@receiver(post_save, sender=Video)
def start_converting_video(sender, instance, created, **kwargs):
    """Queue a conversion whenever the video file was added or replaced."""
    previous = getattr(instance, '_stored_file', None)
    if not created and previous == instance.video_file.name:
        return

    def enqueue_conversion():
        django_rq.get_queue('low').enqueue(
            convert_video, instance.id,
            job_timeout=settings.HLS_JOB_TIMEOUT)

    transaction.on_commit(lambda: drop_replaced_source(previous))
    transaction.on_commit(enqueue_conversion)


@receiver(post_delete, sender=Video)
def delete_video_files(sender, instance, **kwargs):
    remove_video_files(instance)