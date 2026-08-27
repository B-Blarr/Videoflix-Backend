"""Database model for an uploaded video and its HLS output."""

from django.db import models


class Video(models.Model):
    """One uploaded video with its conversion state and results."""

    class Status(models.TextChoices):
        """States a video moves through while the RQ job runs."""
        PENDING = 'pending', 'PENDING'
        PROCESSING = 'processing', 'PROCESSING'
        DONE = 'done', 'DONE'
        FAILED = 'failed', 'FAILED'

    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    video_file = models.FileField(upload_to='videos/')
    status = models.CharField(
        max_length=20, choices=Status.choices, default='pending')
    thumbnail = models.FileField(upload_to='thumbnails/', blank=True, null=True)
    category = models.CharField(max_length=200)
    duration = models.FloatField(null=True, blank=True)
    available_resolutions = models.JSONField(default=list, blank=True)

    class Meta:
        """Order newest first; the frontend shows the first as hero."""
        ordering = ['-created_at']

    def __str__(self):
        """Return the title so the admin lists videos by name."""
        return self.title
    