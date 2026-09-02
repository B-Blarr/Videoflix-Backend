"""Serializers for registration, login and password reset."""

from django.contrib.auth import password_validation, get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from rest_framework import serializers
from rest_framework.validators import UniqueValidator


User = get_user_model()

GENERIC_INPUT_ERROR = "Please check your input and try again."


class RegistrationSerializer(serializers.ModelSerializer):
    """Create an inactive account that an activation mail unlocks."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        """Write-only password, generic message for a taken email."""
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
        """Run Django's password validators on the raw password."""

        password_validation.validate_password(value)
        return value

    def validate(self, attrs):
        """Reject the payload when the two passwords differ."""

        if attrs['password'] != attrs['confirmed_password']:
            raise serializers.ValidationError(
                {'confirmed_password': 'Passwords do not match'})
        return attrs

    def create(self, validated_data):
        """Create the user inactive, with the email as username too."""

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
    """Token serializer that adds the user block to the answer."""

    def validate(self, attrs):
        """Return the token pair plus id and email as "username"."""

        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'username': self.user.email,
        }
        return data


class PasswordResetSerializer(serializers.Serializer):
    """Take only the email address a reset link should go to."""

    email = serializers.EmailField()


class PasswordConfirmSerializer(serializers.Serializer):
    """Take and check the new password behind a reset link."""

    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        """Run Django's password validators on the new password."""

        password_validation.validate_password(value)
        return value

    def validate(self, attrs):
        """Reject the payload when the two passwords differ."""

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
    """Documents the refresh answer, which adds "detail" to the token."""

    detail = serializers.CharField()
    access = serializers.CharField()


class RegistrationUserSerializer(serializers.Serializer):
    """The user block of the registration answer."""

    id = serializers.IntegerField()
    email = serializers.EmailField()


class RegistrationResponseSerializer(serializers.Serializer):
    """Documents the registration answer with its demonstration token."""

    user = RegistrationUserSerializer()
    token = serializers.CharField()
