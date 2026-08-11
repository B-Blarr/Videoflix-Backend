from django.contrib.auth.tokens import default_token_generator
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import RegistrationSerializer, CookieTokenObtainPairSerializer
from .utils import set_auth_cookie, unauthorized, bad_request
from auth_app.utils import get_user_from_uidb64


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