"""Admin registration for the Video model."""

from django.contrib import admin

from video_app.models import Video


class VideoAdmin(admin.ModelAdmin):
    """Admin for videos, showing the conversion result at a glance."""

    list_display = ('title', 'category', 'status', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'status', 'thumbnail', 'duration',
                       'available_resolutions')


admin.site.register(Video, VideoAdmin)
