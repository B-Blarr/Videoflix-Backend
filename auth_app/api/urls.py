from django.urls import path
from .views import RegistrationView, ActivateView, CookieTokenObtainPairView,\
    CookieTokenRefreshView, LogoutView, PasswordConfirmView, PasswordResetView

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='register'),
    path('activate/<uidb64>/<token>/', ActivateView.as_view(), name='activate'),
    path('login/', CookieTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password_reset/', PasswordResetView.as_view(), name='password_reset'),
    path('password_confirm/<uidb64>/<token>/', PasswordConfirmView.as_view(), name='confirm_password'),
]