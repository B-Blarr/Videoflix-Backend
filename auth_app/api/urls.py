from django.urls import path
from .views import RegistrationView, ActivateView, CookieTokenObtainPairView

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('activate/<uidb64>/<token>/', ActivateView.as_view(), name='activation'),
    path('login/', CookieTokenObtainPairView.as_view(), name='login'),
]