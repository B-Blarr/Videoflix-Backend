from django.contrib.auth.tokens import default_token_generator
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import RegistrationSerializer


class RegistrationView(APIView):
    """Register a new user account."""

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