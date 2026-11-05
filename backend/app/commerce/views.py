from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Cart, Reservation, CheckoutSession, Order, Payment, Refund, ShippingRate, Shipment, ExportRecord
from .serializers import CartSerializer, ReservationSerializer, CheckoutSessionSerializer, OrderSerializer, PaymentSerializer, RefundSerializer, ShippingRateSerializer, ShipmentSerializer, OrderTrackingSerializer, ExportRecordSerializer
from .services import (
    get_or_create_cart, add_to_cart, remove_from_cart, CartError,
    create_reservation, release_reservation, create_checkout_session,
    place_order, initiate_payment, record_payment_result, request_refund,
    create_shipment, update_shipment_status,
    create_export_record, update_export_compliance,
)


class CartView(APIView):
    """
    GET /api/v1/cart/

    Returns the authenticated customer's cart.
    Creates an empty cart if one doesn't exist yet.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = get_or_create_cart(request.user)
        return Response(CartSerializer(cart).data)


class CartItemView(APIView):
    """
    POST   /api/v1/cart/items/          — add a product to the cart
    DELETE /api/v1/cart/items/{product_id}/ — remove a product from the cart
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"detail": "product_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            add_to_cart(request.user, product_id)
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        cart = get_or_create_cart(request.user)
        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)

    def delete(self, request, product_id):
        try:
            remove_from_cart(request.user, product_id)
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        cart = get_or_create_cart(request.user)
        return Response(CartSerializer(cart).data)


class ReservationView(APIView):
    """
    POST /api/v1/reservations/   — create a reservation
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get("product_id")
        if not product_id:
            return Response({"detail": "product_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            reservation = create_reservation(request.user, product_id)
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ReservationSerializer(reservation).data, status=status.HTTP_201_CREATED)


class ReservationDetailView(APIView):
    """
    GET    /api/v1/reservations/{id}/   — get reservation status
    DELETE /api/v1/reservations/{id}/   — release reservation
    """
    permission_classes = [IsAuthenticated]

    def _get_reservation(self, request, pk):
        try:
            return Reservation.objects.select_related("product__inventory_item").get(
                pk=pk, customer=request.user
            )
        except Reservation.DoesNotExist:
            return None

    def get(self, request, pk):
        reservation = self._get_reservation(request, pk)
        if not reservation:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ReservationSerializer(reservation).data)

    def delete(self, request, pk):
        reservation = self._get_reservation(request, pk)
        if not reservation:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            release_reservation(reservation, actor=request.user.email)
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CheckoutView(APIView):
    """
    POST /api/v1/checkout/

    Creates a checkout session from an active reservation.
    Body: {reservation_id, shipping_address_id, billing_address_id?}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        reservation_id = request.data.get("reservation_id")
        shipping_address_id = request.data.get("shipping_address_id")
        if not reservation_id or not shipping_address_id:
            return Response(
                {"detail": "reservation_id and shipping_address_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            session = create_checkout_session(
                customer=request.user,
                reservation_id=reservation_id,
                shipping_address_id=shipping_address_id,
                billing_address_id=request.data.get("billing_address_id"),
            )
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CheckoutSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class CheckoutDetailView(APIView):
    """
    GET /api/v1/checkout/{id}/

    Returns a checkout session. Used by the payment page.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            session = CheckoutSession.objects.select_related(
                "reservation__product"
            ).get(pk=pk, customer=request.user)
        except CheckoutSession.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CheckoutSessionSerializer(session).data)


class OrderView(APIView):
    """
    POST /api/v1/orders/   — place an order from a checkout session
    GET  /api/v1/orders/   — list the customer's orders
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        checkout_session_id = request.data.get("checkout_session_id")
        if not checkout_session_id:
            return Response(
                {"detail": "checkout_session_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            order = place_order(request.user, checkout_session_id)
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    def get(self, request):
        orders = Order.objects.filter(customer=request.user).prefetch_related("status_logs")
        return Response(OrderSerializer(orders, many=True).data)


class OrderDetailView(APIView):
    """
    GET /api/v1/orders/{id}/   — retrieve a single order
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            order = Order.objects.prefetch_related("status_logs").get(
                pk=pk, customer=request.user
            )
        except Order.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderSerializer(order).data)


class OrderPayView(APIView):
    """
    POST /api/v1/orders/{id}/pay/

    Initiates a payment for an order.
    Body: {"provider": "webxpay"}
    Returns the payment record plus provider-specific data (e.g. redirect URL).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk, customer=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        provider_name = request.data.get("provider")
        if not provider_name:
            return Response({"detail": "provider is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment, provider_data = initiate_payment(order, provider_name)
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"payment": PaymentSerializer(payment).data, "provider_data": provider_data},
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name="dispatch")
class WebXPayWebhookView(APIView):
    """
    POST /api/v1/webhooks/webxpay/

    Receives payment result callbacks from WEBXPAY.
    No authentication — WEBXPAY posts server-to-server.
    Signature validation is performed inside WebXPayProvider.verify().

    Always returns 200 on valid requests so WEBXPAY does not retry.
    Returns 400 only for structurally invalid payloads (missing order_ref).
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        from .payment_providers import get_provider

        payload = request.data
        order_ref = payload.get("order_ref")

        if not order_ref:
            return Response({"detail": "order_ref is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Look up the most recent pending payment for this order
        try:
            payment = (
                Payment.objects
                .select_related("order")
                .filter(order__order_ref=order_ref, provider="webxpay")
                .order_by("-created_at")
                .first()
            )
        except Exception:
            return Response({"detail": "Error looking up payment."}, status=status.HTTP_400_BAD_REQUEST)

        if not payment:
            return Response({"detail": "Payment not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Idempotency — already processed
        if payment.status == Payment.Status.SUCCEEDED:
            return Response({"detail": "Already processed."}, status=status.HTTP_200_OK)

        provider = get_provider("webxpay")
        result = provider.verify(payload)

        record_payment_result(payment, result)

        return Response({"detail": "OK"}, status=status.HTTP_200_OK)


class ShippingRateView(APIView):
    """
    GET  /api/v1/shipping-rates/          — list all rates (public)
    PUT  /api/v1/shipping-rates/{tier}/   — update a rate (staff only)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return []
        return [IsAuthenticated()]

    def get(self, request):
        rates = ShippingRate.objects.all()
        return Response(ShippingRateSerializer(rates, many=True).data)

    def put(self, request, tier):
        if not request.user.is_staff:
            return Response({"detail": "Staff only."}, status=status.HTTP_403_FORBIDDEN)
        from catalog.models import ValueTier
        if tier not in ValueTier.values:
            return Response({"detail": "Invalid value tier."}, status=status.HTTP_400_BAD_REQUEST)
        rate_usd = request.data.get("rate_usd")
        if rate_usd is None:
            return Response({"detail": "rate_usd is required."}, status=status.HTTP_400_BAD_REQUEST)
        shipping_rate, _ = ShippingRate.objects.update_or_create(
            value_tier=tier,
            defaults={"rate_usd": rate_usd},
        )
        return Response(ShippingRateSerializer(shipping_rate).data)


class OrderShipmentView(APIView):
    """
    GET  /api/v1/orders/{id}/shipment/   — customer or staff retrieves shipment
    POST /api/v1/orders/{id}/shipment/   — staff creates a shipment
    PUT  /api/v1/orders/{id}/shipment/   — staff updates shipment status
    """
    permission_classes = [IsAuthenticated]

    def _get_order(self, request, pk):
        """Staff can access any order; customers only their own."""
        try:
            if request.user.is_staff:
                return Order.objects.get(pk=pk)
            return Order.objects.get(pk=pk, customer=request.user)
        except Order.DoesNotExist:
            return None

    def get(self, request, pk):
        order = self._get_order(request, pk)
        if not order:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            shipment = order.shipment
        except Shipment.DoesNotExist:
            return Response({"detail": "No shipment yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ShipmentSerializer(shipment).data)

    def post(self, request, pk):
        if not request.user.is_staff:
            return Response({"detail": "Staff only."}, status=status.HTTP_403_FORBIDDEN)
        order = self._get_order(request, pk)
        if not order:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        carrier = request.data.get("carrier", "").strip()
        try:
            shipment = create_shipment(
                order=order,
                carrier=carrier,
                tracking_number=request.data.get("tracking_number", ""),
                tracking_url=request.data.get("tracking_url", ""),
                estimated_delivery_date=request.data.get("estimated_delivery_date"),
                notes=request.data.get("notes", ""),
                actor=request.user.email,
            )
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ShipmentSerializer(shipment).data, status=status.HTTP_201_CREATED)

    def put(self, request, pk):
        if not request.user.is_staff:
            return Response({"detail": "Staff only."}, status=status.HTTP_403_FORBIDDEN)
        order = self._get_order(request, pk)
        if not order:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            shipment = order.shipment
        except Shipment.DoesNotExist:
            return Response({"detail": "No shipment found."}, status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get("status", "").strip()
        if not new_status:
            return Response({"detail": "status is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            shipment = update_shipment_status(
                shipment=shipment,
                new_status=new_status,
                actor=request.user.email,
                notes=request.data.get("notes", ""),
                actual_delivery_date=request.data.get("actual_delivery_date"),
            )
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ShipmentSerializer(shipment).data)


class OrderTrackingView(APIView):
    """
    GET /api/v1/tracking/{order_ref}/

    Public endpoint — no authentication required.
    Returns a customer-facing tracking summary for an order.
    """
    permission_classes = []
    authentication_classes = []

    def get(self, request, order_ref):
        try:
            order = Order.objects.prefetch_related("status_logs").get(order_ref=order_ref)
        except Order.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderTrackingSerializer(order).data)


class OrderExportView(APIView):
    """
    GET  /api/v1/orders/{id}/export/   — staff retrieves export record
    POST /api/v1/orders/{id}/export/   — staff creates export record
    PUT  /api/v1/orders/{id}/export/   — staff updates compliance status
    """
    permission_classes = [IsAuthenticated]

    def _get_order(self, pk):
        try:
            return Order.objects.select_related(
                "checkout_session__reservation__product__inventory_item"
            ).get(pk=pk)
        except Order.DoesNotExist:
            return None

    def get(self, request, pk):
        if not request.user.is_staff:
            return Response({"detail": "Staff only."}, status=status.HTTP_403_FORBIDDEN)
        order = self._get_order(pk)
        if not order:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            export_record = order.export_record
        except ExportRecord.DoesNotExist:
            return Response({"detail": "No export record yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ExportRecordSerializer(export_record).data)

    def post(self, request, pk):
        if not request.user.is_staff:
            return Response({"detail": "Staff only."}, status=status.HTTP_403_FORBIDDEN)
        order = self._get_order(pk)
        if not order:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            export_record = create_export_record(
                order=order,
                destination_country=request.data.get("destination_country", ""),
                declared_value_usd=request.data.get("declared_value_usd"),
                export_permit_number=request.data.get("export_permit_number", ""),
                customs_declaration_number=request.data.get("customs_declaration_number", ""),
                document_s3_keys=request.data.get("document_s3_keys", ""),
                notes=request.data.get("notes", ""),
                actor=request.user.email,
            )
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ExportRecordSerializer(export_record).data, status=status.HTTP_201_CREATED)

    def put(self, request, pk):
        if not request.user.is_staff:
            return Response({"detail": "Staff only."}, status=status.HTTP_403_FORBIDDEN)
        order = self._get_order(pk)
        if not order:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            export_record = order.export_record
        except ExportRecord.DoesNotExist:
            return Response({"detail": "No export record found."}, status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get("compliance_status", "").strip()
        if not new_status:
            return Response({"detail": "compliance_status is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            export_record = update_export_compliance(
                export_record=export_record,
                new_status=new_status,
                notes=request.data.get("notes", ""),
            )
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ExportRecordSerializer(export_record).data)


class OrderRefundView(APIView):
    """
    POST /api/v1/orders/{id}/refund/

    Staff only. Creates a refund for a confirmed/delivered order.
    Body: {"reason": "..."}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_staff:
            return Response({"detail": "Staff only."}, status=status.HTTP_403_FORBIDDEN)

        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        reason = request.data.get("reason", "").strip()
        if not reason:
            return Response({"detail": "reason is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            refund = request_refund(order, reason=reason, requested_by=request.user.email)
        except CartError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(RefundSerializer(refund).data, status=status.HTTP_201_CREATED)
