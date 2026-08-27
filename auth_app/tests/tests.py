"""Tests for registration, login, token, and password endpoints."""

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.conf import settings
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()
SYNC_QUEUES = {
    name: {**config, 'ASYNC': False}
    for name, config in settings.RQ_QUEUES.items()
}


@override_settings(RQ_QUEUES=SYNC_QUEUES)
class RegistrationTests(APITestCase):
    """Tests for the register endpoint and its activation email."""

    def setUp(self):
        """Create an existing user and a payload for a fresh signup."""
        self.user = User.objects.create_user(
            username='test@test.de', password='SuperSecret123!',
            email='test@test.de')
        self.url = reverse('register')
        self.data = {
            'email': 'new@test.de',
            'password': 'SuperSecret123!',
            'confirmed_password': 'SuperSecret123!',
        }

    def test_registration(self):
        """Registering with valid data creates the account."""
        url = reverse('register')
        data = {
            'email': 'new@test.de',
            'password': 'SuperSecret123!',
            'confirmed_password': 'SuperSecret123!',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(User.objects.filter(email='new@test.de').exists())

    def test_registration_sends_activation_email(self):
        """Registering mails one activation link once the commit fires."""
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url, self.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['new@test.de'])
        self.assertIn("activate.html", mail.outbox[0].body)

    def test_registration_password_mismatch_returns_400(self):
        """Mismatched passwords are rejected on the confirmation field."""
        url = reverse('register')
        data = {
            'email': 'new@test.de',
            'password': 'SuperSecret123!',
            'confirmed_password': 'differentpassword',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('confirmed_password', response.data)

    def test_registration_email_exists_returns_400(self):
        """Signing up with an address that already exists is rejected."""
        url = reverse('register')
        data = {
            'email': 'test@test.de',
            'password': 'SuperSecret123!',
            'confirmed_password': 'SuperSecret123!',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('email', response.data)


class LoginTests(APITestCase):
    """Tests for logging in with an email and receiving cookies."""

    def setUp(self):
        """Create an activated account to log in with."""
        self.user = User.objects.create_user(
            username='test@test.de', password='SuperSecret123!',
            email='test@test.de')

    def test_login(self):
        """Logging in returns the email as username and sets cookies."""
        url = reverse('login')
        data = {'email': 'test@test.de', 'password': 'SuperSecret123!'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['user']['username'], 'test@test.de')
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)


class LogoutTests(APITestCase):
    """Tests for logging out and invalidating the refresh token."""

    def setUp(self):
        """Create an account and log it in so the cookies are set."""

        self.user = User.objects.create_user(
            username='test@test.de', password='SuperSecret123!',
            email='test@test.de')
        self.client.post(
            reverse('login'),
            {'email': 'test@test.de', 'password': 'SuperSecret123!'},
            format='json',
        )

    def test_logout(self):
        """Logging out clears both auth cookies and returns a detail."""

        url = reverse('logout')
        response = self.client.post(url)
        self.assertEqual(
            response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.cookies['access_token'].value, '')
        self.assertEqual(response.cookies['refresh_token'].value, '')
        self.assertIn('detail', response.data)

    def test_user_already_logged_out_returns_401(self):
        """Replaying the cookies of a logged out session is rejected."""

        access = self.client.cookies['access_token'].value
        refresh = self.client.cookies['refresh_token'].value
        self.client.post(reverse('logout'))
        self.client.cookies['access_token'] = access
        self.client.cookies['refresh_token'] = refresh
        response = self.client.post(reverse('logout'))
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.data)
        self.assertEqual(response.cookies['access_token'].value, '')
        self.assertEqual(response.cookies['refresh_token'].value, '')


class TokenRefreshTests(APITestCase):
    """Tests for refreshing the access token from the cookie."""

    def setUp(self):
        """Create an account and log it in to get a refresh cookie."""
        self.user = User.objects.create_user(
            username='test@test.de', password='SuperSecret123!',
            email='test@test.de')
        self.client.post(
            reverse('login'),
            {'email': 'test@test.de', 'password': 'SuperSecret123!'},
            format='json',
        )

    def test_token_refresh(self):
        """Refreshing with a valid cookie returns a new access token."""
        url = reverse('token_refresh')
        response = self.client.post(url)
        self.assertEqual(
            response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['detail'], 'Token refreshed')
        self.assertIn('access_token', response.cookies)

    def test_token_refresh_without_login_returns_400(self):
        """Refreshing without a refresh cookie is a 400, not a 401."""
        client = APIClient()
        response = client.post(reverse('token_refresh'))
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_token_refresh_with_invalid_token_returns_401(self):
        """Refreshing with an unusable refresh cookie gives 401."""
        client = APIClient()
        client.cookies['refresh_token'] = 'not-a-valid-token'
        response = client.post(reverse('token_refresh'))
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.data)


class ActivateTests(APITestCase):
    """Tests for activating an account from the emailed link."""

    def setUp(self):
        """Create an inactive account plus a valid uid and token."""
        self.user = User.objects.create_user(
            username='test@test.de', password='SuperSecret123!',
            email='test@test.de', is_active=False)
        self.uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)

    def test_activate(self):
        """Following a valid activation link activates the account."""
        url = reverse('activate', args=[self.uidb64, self.token])
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            response.data['message'], 'Account successfully activated.')
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_invalid_token_returns_400(self):
        """Activating with a token that does not match gives 400."""
        url = reverse('activate', args=[self.uidb64, 'invalid-token'])
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_invalid_uidb_returns_400(self):
        """Activating with an undecodable uid gives 400, not a 500."""
        url = reverse('activate', args=['invalid-uidb', self.token])
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.data)


@override_settings(RQ_QUEUES=SYNC_QUEUES)
class PasswordResetTests(APITestCase):
    """Tests the reset endpoint: it sends mail, but never reveals to whom."""

    def setUp(self):
        """Create an account and remember the reset endpoint URL."""
        self.user = User.objects.create_user(
            username='test@test.de', password='SuperSecret123!',
            email='test@test.de')
        self.url = reverse('password_reset')

    def test_password_reset_send_email(self):
        """A known address gets one mail with the reset link on commit."""
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                self.url, {'email': 'test@test.de'}, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('confirm_password.html', mail.outbox[0].body)

    def test_password_reset_unknown_email_returns_200(self):
        """An unknown address still gets 200 and no mail is sent."""
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                self.url, {'email': 'unknown@unknown.de'}, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_invalid_input_returns_200(self):
        """Missing or malformed input still gets 200 and sends no mail."""
        for payload in ({}, {'email': 'kaputt'}):
            with self.subTest(payload=payload):
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.post(
                        self.url, payload, format='json')
                self.assertEqual(
                    response.status_code, status.HTTP_200_OK, response.data)
                self.assertEqual(len(mail.outbox), 0)


class PasswordConfirmTests(APITestCase):
    """Tests for setting a new password from the emailed link."""
    def setUp(self):
        """Create an account, a valid reset link, and a new password."""
        self.user = User.objects.create_user(
            username='test@test.de', password='SuperSecret123!',
            email='test@test.de')
        self.uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)
        self.url = reverse(
            'password_confirm', args=[self.uidb64, self.token])
        self.data = {
            'new_password': 'MynewSecret123!',
            'confirm_password': 'MynewSecret123!',
        }

    def test_password_confirm(self):
        """Confirming with matching passwords replaces the old one."""
        response = self.client.post(self.url, self.data, format='json')
        self.assertEqual(
            response.status_code, status.HTTP_200_OK, response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('MynewSecret123!'))
