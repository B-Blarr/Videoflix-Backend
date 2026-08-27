from django.contrib.auth import password_validation, get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from rest_framework import serializers
from rest_framework.validators import UniqueValidator


User = get_user_model()

GENERIC_INPUT_ERROR = "Please check your input and try again."

class RegistrationSerializer(serializers.ModelSerializer):

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'confirmed_password']
        extra_kwargs = {
            'password': {
                'write_only': True
            },
            'email': {
                'validators': [
                    UniqueValidator(
                        queryset=User.objects.all(),
                        message=GENERIC_INPUT_ERROR,
                    )
                ]
            },
        }

    def validate_password(self, value):

        password_validation.validate_password(value)
        return value

    def validate(self, attrs):

        if attrs['password'] != attrs['confirmed_password']:
            raise serializers.ValidationError(
                {'confirmed_password': 'Passwords do not match'})
        return attrs

    def create(self, validated_data):

        pw = validated_data['password']
        account = User(
            email=validated_data['email'],
            username=validated_data['email'],
            is_active=False
        )
        account.set_password(pw)
        account.save()
        return account


class CookieTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
 
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'username': self.user.email,
        }
        return data


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):

        password_validation.validate_password(value)
        return value

    def validate(self, attrs):

        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {'confirm_password': 'Passwords do not match'})
        return attrs


class DetailResponseSerializer(serializers.Serializer):
    """Documents the plain {"detail": ...} answers."""

    detail = serializers.CharField()


class LoginUserSerializer(serializers.Serializer):
    """The user block of the login answer. "username" carries the email."""

    id = serializers.IntegerField()
    username = serializers.EmailField()


class LoginResponseSerializer(serializers.Serializer):
    """Documents the login answer, which replaces the simplejwt token pair."""

    detail = serializers.CharField()
    user = LoginUserSerializer()


class RefreshResponseSerializer(serializers.Serializer):
    """Documents the refresh answer, which adds "detail" to the access token."""

    detail = serializers.CharField()
    access = serializers.CharField()
