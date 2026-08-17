from django.db import models


class Video(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    video_file = models.FileField(upload_to='videos/')
    thumbnail = models.FileField(upload_to='thumbnails/', blank=True, null=True)
    category = models.CharField(max_length=200)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    