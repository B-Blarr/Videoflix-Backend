"""Admin registration for the Video model."""

from django.contrib import admin

from video_app.models import Video


admin.site.register(Video)
