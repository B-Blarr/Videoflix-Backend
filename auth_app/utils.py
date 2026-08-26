import os

from django.conf import settings
from email.mime.image import MIMEImage
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode


User = get_user_model()


def build_activation_link(user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f"{settings.FRONTEND_URL}/pages/auth/activate.html?uid={uidb64}&token={token}"


def send_activation_email(user):
    link = build_activation_link(user)
    html_body = render_to_string('email_activation.html', {'link': link})
    mail = EmailMultiAlternatives(
        subject='Confirm your email',
        body=f'Please confirm your email address: {link}',
        to=[user.email],
    )
    mail.attach_alternative(html_body, 'text/html')
    mail.send()


def get_user_from_uidb64(uidb64):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        return User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


def build_password_reset_link(user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f"{settings.FRONTEND_URL}/pages/auth/confirm_password.html?uid={uidb64}&token={token}"


def send_password_reset_email(user):
    link = build_password_reset_link(user)
    send_mail(
        subject="Reset your password",
        message=f"Please click on the link to change your password: {link}",
        from_email=None,
        recipient_list=[user.email],
        fail_silently=False,
    )


def attach_logo(mail):
    """Attach the logo so it can be displayed inside the email body."""
    path = os.path.join(settings.BASE_DIR, 'auth_app', 'static', 'logo.png')
    with open(path, 'rb') as logo:
        image = MIMEImage(logo.read())
    image.add_header('Content-ID', '<logo>')
    image.add_header('Content-Disposition', 'inline', filename='logo.png')
    mail.attach(image)
    mail.mixed_subtype = 'related'