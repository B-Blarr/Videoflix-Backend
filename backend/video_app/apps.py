"""App config for video_app, wiring up the video signals."""

from django.apps import AppConfig


class VideoAppConfig(AppConfig):
    """App config that connects the video signals on startup."""
    name = 'video_app'

    def ready(self):
        """Import the signal handlers so they get connected."""
        from . import signals # noqa:401
