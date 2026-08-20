from django.dispatch import receiver
from django.db.models.signals import post_save

from .models import Video
from .utils import convert_video


@receiver(post_save, sender=Video)
def start_converting_video(sender, instance, created, **kwargs):
    if not created:
        return
    convert_video(instance.id)