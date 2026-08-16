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