"""JWT authentication that reads the token from a cookie."""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CookieJWTAuthentication(JWTAuthentication):
    """Read the JWT access token from a cookie instead of the header."""

    def authenticate(self, request):
        """Return the user and token from the access_token cookie."""
        raw_token = request.COOKIES.get('access_token')
        if not raw_token:
            return None
        try:
            validated_token = self.get_validated_token(raw_token)
        except InvalidToken:
            return None
        return self.get_user(validated_token), validated_token