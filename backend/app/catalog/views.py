from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Product
from .serializers import ProductListSerializer, ProductDetailSerializer
from .filters import ProductFilter
from .services.media_signing import generate_signed_urls


class ProductListView(ListAPIView):
    serializer_class = ProductListSerializer
    filterset_class = ProductFilter

    def get_queryset(self):
        return (
            Product.objects.select_related(
                "inventory_item__physical_gemstone__species",
                "inventory_item__physical_gemstone__variety",
            )
            .prefetch_related("media")
            .filter(listing_status__in=["active", "paused", "sold_out"])
            .order_by("-created_at")
        )


class ProductDetailView(RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Product.objects.select_related(
                "inventory_item__physical_gemstone__species",
                "inventory_item__physical_gemstone__variety",
            )
            .prefetch_related(
                "media",
                "inventory_item__physical_gemstone__certification_reports__laboratory",
            )
            .filter(listing_status__in=["active", "paused", "sold_out"])
        )


class MediaSignedUrlView(APIView):
    """
    POST /api/v1/catalog/media/sign/

    Request body:
        {"keys": ["media/gems/CEY-COR-2026-000001/01.jpg", ...]}

    Response:
        {"signed_urls": {"media/gems/.../01.jpg": "https://...", ...}}

    Returns null for any key that could not be signed
    (bucket not configured, credentials missing, key not found).
    Max 20 keys per request to prevent abuse.
    """
    MAX_KEYS = 20

    def post(self, request):
        keys = request.data.get("keys", [])
        if not isinstance(keys, list):
            return Response(
                {"detail": "'keys' must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(keys) > self.MAX_KEYS:
            return Response(
                {"detail": f"Maximum {self.MAX_KEYS} keys per request."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not all(isinstance(k, str) and k.strip() for k in keys):
            return Response(
                {"detail": "All keys must be non-empty strings."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        signed = generate_signed_urls(keys)
        return Response({"signed_urls": signed})
