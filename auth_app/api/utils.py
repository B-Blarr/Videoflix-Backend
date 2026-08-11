from django.conf import settings
from rest_framework import status
from rest_framework.response import Response


def set_auth_cookie(response, key, token):
    """Attach a JWT as an HttpOnly cookie to the given response."""
    response.set_cookie(
        key=key,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite='Lax',
    )


def unauthorized(detail):
    """Return a 401 response with the given detail message."""
    return Response({'detail': detail}, status=status.HTTP_401_UNAUTHORIZED)


def bad_request(detail):
    """Return a 400 response with the given detail message."""
    return Response({'detail': detail}, status=status.HTTP_400_BAD_REQUEST)
