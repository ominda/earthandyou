from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers import RegisterSerializer, LoginSerializer, CustomerSerializer
from .services import issue_tokens, create_verification_token, verify_email_token


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

    Returns the authenticated customer's profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CustomerSerializer(request.user).data)
