from rest_framework import serializers
from .models import Cart, CartItem, Reservation, CheckoutSession, Order, OrderStatusLog, Payment, Refund, ShippingRate, Shipment, ExportRecord


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    gemstone_id = serializers.CharField(source="product.gemstone_id", read_only=True)
    headline = serializers.CharField(source="product.headline", read_only=True)
    price_usd = serializers.DecimalField(
        source="product.price_usd", max_digits=12, decimal_places=2, read_only=True
    )
    slug = serializers.CharField(source="product.slug", read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product_id", "gemstone_id", "headline", "price_usd", "slug", "added_at"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(source="items.count", read_only=True)
    total_usd = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "item_count", "total_usd", "items", "updated_at"]

    def get_total_usd(self, obj):
        return sum(item.product.price_usd for item in obj.items.all())


class ReservationSerializer(serializers.ModelSerializer):
    gemstone_id = serializers.CharField(source="product.gemstone_id", read_only=True)
    headline = serializers.CharField(source="product.headline", read_only=True)
    price_usd = serializers.DecimalField(
        source="product.price_usd", max_digits=12, decimal_places=2, read_only=True
    )
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id", "gemstone_id", "headline", "price_usd",
            "status", "is_active", "expires_at", "created_at",
        ]


class CheckoutSessionSerializer(serializers.ModelSerializer):
    gemstone_id = serializers.CharField(source="reservation.product.gemstone_id", read_only=True)
    headline = serializers.CharField(source="reservation.product.headline", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = CheckoutSession
        fields = [
            "id", "gemstone_id", "headline",
            "shipping_address", "billing_address",
            "subtotal_usd", "shipping_usd", "total_usd",
            "status", "is_active", "expires_at", "created_at",
        ]


class OrderStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusLog
        fields = ["from_status", "to_status", "actor", "notes", "created_at"]


class OrderSerializer(serializers.ModelSerializer):
    status_logs = OrderStatusLogSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_ref",
            "gemstone_id", "product_headline", "product_slug",
            "subtotal_usd", "shipping_usd", "total_usd",
            "shipping_address", "billing_address",
            "status", "payment_reference",
            "status_logs", "created_at",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "provider", "provider_reference", "amount_usd", "status", "created_at"]


class ShippingRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingRate
        fields = ["id", "value_tier", "rate_usd", "updated_at"]


class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = [
            "id", "carrier", "tracking_number", "tracking_url",
            "status", "estimated_delivery_date", "actual_delivery_date",
            "notes", "created_at", "updated_at",
        ]


class OrderTrackingSerializer(serializers.ModelSerializer):
    """
    Public-facing tracking summary. Keyed by order_ref.
    Exposes only what a customer needs to track their order —
    no pricing, no address details, no internal IDs.
    """
    timeline = serializers.SerializerMethodField()
    shipment = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "order_ref", "gemstone_id", "product_headline",
            "status", "created_at", "shipment", "timeline",
        ]

    def get_timeline(self, obj):
        return [
            {
                "status": log.to_status,
                "timestamp": log.created_at,
            }
            for log in obj.status_logs.all()
        ]

    def get_shipment(self, obj):
        try:
            s = obj.shipment
        except Exception:
            return None
        return {
            "carrier": s.carrier,
            "tracking_number": s.tracking_number,
            "tracking_url": s.tracking_url,
            "status": s.status,
            "estimated_delivery_date": s.estimated_delivery_date,
            "actual_delivery_date": s.actual_delivery_date,
        }


class ExportRecordSerializer(serializers.ModelSerializer):
    documents = serializers.ListField(read_only=True)

    class Meta:
        model = ExportRecord
        fields = [
            "id", "export_permit_number", "customs_declaration_number",
            "declared_value_usd", "destination_country", "compliance_status",
            "documents", "notes", "created_at", "updated_at",
        ]


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = [
            "id", "amount_usd", "reason", "status",
            "provider_reference", "requested_by", "created_at",
        ]
