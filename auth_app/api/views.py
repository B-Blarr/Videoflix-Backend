"""Views for registration, activation, login and password reset."""

from django.contrib.auth.tokens import default_token_generator
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView)

from .serializers import (RegistrationSerializer,
                          CookieTokenObtainPairSerializer,
                          PasswordResetSerializer, PasswordConfirmSerializer,
                          DetailResponseSerializer, LoginResponseSerializer,
                          RefreshResponseSerializer,
                          RegistrationResponseSerializer)
from .utils import (set_auth_cookie, clear_auth_cookies, unauthorized,
                    bad_request)
from auth_app.utils import get_user_from_uidb64, enqueue_password_reset_email

LOGOUT_DETAIL = (
    "Logout successful! All tokens will be deleted. "
    "Refresh token is now invalid."
)

PASSWORD_RESET_DETAIL = ("An email has been sent to reset your password.")

PASSWORD_CONFIRM_DETAIL = ("Your Password has been successfully reset.")


@extend_schema(responses=RegistrationResponseSerializer)
class RegistrationView(GenericAPIView):
    """Register an inactive account and return its activation token."""

    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer

    def post(self, request):
        """Create the account and answer with its id, email and token."""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'user': {'id': user.id, 'email': user.email},
                'token': default_token_generator.make_token(user),
            },
            status=status.HTTP_201_CREATED,
        )


class ActivateView(APIView):
    """Activate an account from the link in the activation mail."""

    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        """Activate the account, answering under "message" not "detail"."""
        user = get_user_from_uidb64(uidb64)
        if (user is None
                or not default_token_generator.check_token(user, token)):
            return Response(
                {"message": "Activation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = True
        user.save()
        return Response({"message": "Account successfully activated."})


@extend_schema(responses=LoginResponseSerializer)
class CookieTokenObtainPairView(TokenObtainPairView):
    """Log in by email and hand the tokens over as cookies."""

    serializer_class = CookieTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        """Set both token cookies and replace the body per contract."""

        response = super().post(request, *args, **kwargs)
        user = response.data.get('user')
        set_auth_cookie(
            response, 'access_token', response.data.get('access'))
        set_auth_cookie(
            response, 'refresh_token', response.data.get('refresh'))
        response.data = {
            "detail": "Login successful",
            "user": user
        }
        return response


@extend_schema(request=None, responses=RefreshResponseSerializer)
class CookieTokenRefreshView(TokenRefreshView):
    """Refresh the access token from the refresh_token cookie."""

    def post(self, request, *args, **kwargs):
        """Issue a new access token and refresh its cookie."""

        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token is None:
            return bad_request('Refresh token not found!')
        serializer = self.get_serializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            return unauthorized('Refresh token invalid!')
        access = serializer.validated_data.get('access')
        response = Response({'detail': 'Token refreshed', 'access': access})
        set_auth_cookie(response, 'access_token', access)

        return response


@extend_schema(request=None, responses=DetailResponseSerializer)
class LogoutView(APIView):
    """Log out by blacklisting the refresh token from the cookie."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Blacklist the refresh token and drop both cookies."""
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token is None:
            return bad_request('Refresh token not found!')
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return clear_auth_cookies(
                unauthorized('User is already logged out!'))
        response = Response(
            {'detail': LOGOUT_DETAIL}, status=status.HTTP_200_OK)
        return clear_auth_cookies(response)


@extend_schema(responses=DetailResponseSerializer)
class PasswordResetView(GenericAPIView):
    """Send a reset link without revealing whether the account exists."""

    permission_classes = [AllowAny]
    serializer_class = PasswordResetSerializer

    def post(self, request):
        """Queue the mail if valid, but answer 200 either way."""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            enqueue_password_reset_email(serializer.validated_data['email'])
        return Response({'detail': PASSWORD_RESET_DETAIL})


@extend_schema(responses=DetailResponseSerializer)
class PasswordConfirmView(GenericAPIView):
    """Set a new password for the user behind a reset link."""

    permission_classes = [AllowAny]
    serializer_class = PasswordConfirmSerializer

    def post(self, request, uidb64, token):
        """Set the new password, or answer 400 if the link is stale."""
        user = get_user_from_uidb64(uidb64)
        if (user is None
                or not default_token_generator.check_token(user, token)):
            return bad_request("Invalid or expired reset link.")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"detail": PASSWORD_CONFIRM_DETAIL})
