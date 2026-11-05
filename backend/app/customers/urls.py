from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, LogoutView, VerifyEmailView,
    MeView, ProfileView, AddressListView, AddressDetailView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("me/profile/", ProfileView.as_view(), name="auth-me-profile"),
    path("me/addresses/", AddressListView.as_view(), name="auth-me-addresses"),
    path("me/addresses/<int:pk>/", AddressDetailView.as_view(), name="auth-me-address-detail"),
]
