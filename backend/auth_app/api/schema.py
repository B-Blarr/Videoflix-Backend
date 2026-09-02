"""OpenAPI extensions for drf-spectacular.

Importing this module registers the extensions, which is why ``apps.py``
pulls it in on startup.
"""
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CookieJWTScheme(OpenApiAuthenticationExtension):
    """Describe the cookie based JWT so the schema gains a security scheme."""

    target_class = 'auth_app.api.authentication.CookieJWTAuthentication'
    name = 'cookieAuth'

    def get_security_definition(self, auto_schema):
        """Return the OpenAPI definition of the access token cookie."""
        return {
            'type': 'apiKey',
            'in': 'cookie',
            'name': 'access_token',
        }
