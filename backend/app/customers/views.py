from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenRefreshView
from .models import CustomerAddress, CustomerProfile, StaffProfile
from .serializers import (
    RegisterSerializer, LoginSerializer, CustomerSerializer,
    CustomerProfileSerializer, CustomerAddressSerializer, StaffProfileSerializer,
)
from .services import issue_tokens, create_verification_token, verify_email_token
from .permissions import IsStaff, HasRole


class RegisterView(APIView):
    """
    POST /api/v1/auth/register/

    Creates a new customer account and issues JWT tokens.
    A verification token is created — in production this would trigger
    an email (notification layer is Phase 6).
    """

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        create_verification_token(customer)
        tokens = issue_tokens(customer)
        return Response(
            {
                **tokens,
                "user": CustomerSerializer(customer).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/v1/auth/login/

    Authenticates a customer and returns JWT tokens.
    """

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = serializer.validated_data["user"]
        tokens = issue_tokens(customer)
        return Response(
            {
                **tokens,
                "user": CustomerSerializer(customer).data,
            }
        )


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/

    Invalidates the refresh token by blacklisting it.
    Requires authentication.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken
        from rest_framework_simplejwt.exceptions import TokenError
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerifyEmailView(APIView):
    """
    POST /api/v1/auth/verify-email/

    Verifies a customer's email address using the token sent via email.
    Body: {"token": "<uuid>"}
    """

    def post(self, request):
        token_value = request.data.get("token")
        if not token_value:
            return Response(
                {"detail": "Token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        customer = verify_email_token(token_value)
        if not customer:
            return Response(
                {"detail": "Invalid or expired verification token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Email verified successfully."})


class MeView(APIView):
    """
    GET /api/v1/auth/me/
    PATCH /api/v1/auth/me/

    Returns or updates the authenticated customer's core fields.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CustomerSerializer(request.user).data)

    def patch(self, request):
        serializer = CustomerSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProfileView(APIView):
    """
    GET /api/v1/auth/me/profile/
    PATCH /api/v1/auth/me/profile/

    Returns or updates the customer's extended profile.
    Profile is created on first GET if it doesn't exist.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = CustomerProfile.objects.get_or_create(customer=request.user)
        return Response(CustomerProfileSerializer(profile).data)

    def patch(self, request):
        profile, _ = CustomerProfile.objects.get_or_create(customer=request.user)
        serializer = CustomerProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AddressListView(APIView):
    """
    GET  /api/v1/auth/me/addresses/   — list all addresses
    POST /api/v1/auth/me/addresses/   — create a new address
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = CustomerAddress.objects.filter(customer=request.user)
        return Response(CustomerAddressSerializer(qs, many=True).data)

    def post(self, request):
        serializer = CustomerAddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(customer=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AddressDetailView(APIView):
    """
    GET    /api/v1/auth/me/addresses/{id}/
    PATCH  /api/v1/auth/me/addresses/{id}/
    DELETE /api/v1/auth/me/addresses/{id}/
    """
    permission_classes = [IsAuthenticated]

    def _get_address(self, request, pk):
        try:
            return CustomerAddress.objects.get(pk=pk, customer=request.user)
        except CustomerAddress.DoesNotExist:
            return None

    def get(self, request, pk):
        address = self._get_address(request, pk)
        if not address:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CustomerAddressSerializer(address).data)

    def patch(self, request, pk):
        address = self._get_address(request, pk)
        if not address:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = CustomerAddressSerializer(address, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        address = self._get_address(request, pk)
        if not address:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        address.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StaffMeView(APIView):
    """
    GET /api/v1/staff/me/

    Returns the authenticated staff user's role and profile info.
    Requires is_staff=True and a StaffProfile to exist.
    """
    permission_classes = [IsStaff]

    def get(self, request):
        try:
            profile = request.user.staff_profile
        except StaffProfile.DoesNotExist:
            return Response(
                {"detail": "Staff profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(StaffProfileSerializer(profile).data)
