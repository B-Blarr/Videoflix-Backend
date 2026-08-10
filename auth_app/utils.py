from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def build_activation_link(user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f"{settings.FRONTEND_URL}/pages/auth/activate.html?uid={uidb64}&token={token}"


def send_activation_email(user):
    link = build_activation_link(user)
    send_mail(
        subject="Confirm your email",
        message=f"Please confirm your email address: {link}",
        from_email=None,
        recipient_list=[user.email],
        fail_silently=False,
    )

