"""App config for auth_app, loading its signals on startup."""

from django.apps import AppConfig


class AuthAppConfig(AppConfig):
    """App config that wires up signals and schema extensions."""

    name = 'auth_app'

    def ready(self):
        """Import signals and the schema extension once apps load."""
        from . import signals # noqa:401
        from .api import schema # noqa:401
