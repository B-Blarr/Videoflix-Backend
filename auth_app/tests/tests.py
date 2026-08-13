from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()


class RegistrationTests(APITestCase):
    """Tests for POST /api/register/."""

    def setUp(self):
 
        self.user = User.objects.create_user(
            username='test@test.de', password='SuperSecret123!',
            email='test@test.de')

    def test_registration(self):
        """A valid payload creates the user and returns 201."""
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