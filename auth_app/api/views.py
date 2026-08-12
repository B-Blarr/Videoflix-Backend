from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import RegistrationSerializer, CookieTokenObtainPairSerializer,\
    PasswordResetSerializer, PasswordConfirmSerializer
from .utils import set_auth_cookie, unauthorized, bad_request
from auth_app.utils import get_user_from_uidb64, send_password_reset_email

User = get_user_model()

LOGOUT_DETAIL = (
    "Logout successful! All tokens will be deleted. "
    "Refresh token is now invalid."
)

PASSWORD_RESET_DETAIL = ("An email has been sent to reset your password.")

PASSWORD_CONFIRM_DETAIL = ("Your Password has been successfully reset.")


class RegistrationView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
    
        serializer = RegistrationSerializer(data=request.data)

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

    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        user = get_user_from_uidb64(uidb64)
        if user is None or not default_token_generator.check_token(user, token):
            return Response(
                {"message": "Activation failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = True
        user.save()
        return Response({"message": "Account successfully activated."})


class CookieTokenObtainPairView(TokenObtainPairView):

    serializer_class = CookieTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):

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


class CookieTokenRefreshView(TokenRefreshView):

    def post(self, request, *args, **kwargs):

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


class LogoutView(APIView):

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token is None:
            return bad_request('Refresh token not found!')
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return unauthorized('User is already logged out!')
        response = Response(
            {'detail': LOGOUT_DETAIL}, status=status.HTTP_200_OK)
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response


class PasswordResetView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email=serializer.validated_data["email"]).first()
        if user is not None:
            send_password_reset_email(user)
        return Response({"detail": PASSWORD_RESET_DETAIL})


class PasswordChangeView(APIView):

    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        user = get_user_from_uidb64(uidb64)
        if user is None or not default_token_generator.check_token(user, token):
            return bad_request("Invalid or expired reset link.")
        serializer = PasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"detail": PASSWORD_CONFIRM_DETAIL})