from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """Read the JWT access token from a cookie instead of the header."""

    def authenticate(self, request):
        """Return the user and token from the access_token cookie."""
        raw_token = request.COOKIES.get('access_token')
        if not raw_token:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token