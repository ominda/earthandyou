import datetime
from decimal import Decimal
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from catalog.models import GemstoneSpecies, Product, ValueTier
from inventory.models import PhysicalGemstone, InventoryItem, ListingStatus
from customers.models import Customer, CustomerAddress
from commerce.models import Order, Shipment, ExportRecord
from commerce.services import (
    create_reservation, create_checkout_session, place_order,
    initiate_payment, record_payment_result,
    create_shipment, update_shipment_status,
    create_export_record, update_export_compliance, CartError,
)
from commerce.payment_providers import PaymentResult


WEBXPAY_SETTINGS = {
    "WEBXPAY_MERCHANT_ID": "TEST_MERCHANT",
    "WEBXPAY_SECRET_KEY": "test-secret-key",
    "WEBXPAY_API_URL": "https://payment.webxpay.com/",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_customer(email="buyer@example.com", password="StrongPass1!", is_staff=False):
    return Customer.objects.create_user(email=email, password=password, is_staff=is_staff)


def make_processing_order(customer, species_code="EX1"):
    species, _ = GemstoneSpecies.objects.get_or_create(
        code=species_code,
        defaults={"name": f"Species-{species_code}", "common_name": "Test"},
    )
    gemstone = PhysicalGemstone.objects.create(
        species=species, acquisition_date=datetime.date.today()
    )
    inventory = InventoryItem.objects.create(
        physical_gemstone=gemstone,
        listing_status=ListingStatus.ACTIVE,
        is_reserved=False,
        is_sold=False,
    )
    product = Product.objects.create(
        inventory_item=inventory,
        price_usd=Decimal("3000.00"),
        listing_status=ListingStatus.ACTIVE,
        value_tier=ValueTier.LUXURY,
        headline="Test Gem",
    )
    reservation = create_reservation(customer, product.pk)
    address = CustomerAddress.objects.create(
        customer=customer,
        address_type="shipping",
        recipient_name="Ada Lovelace",
        line1="123 Gem St",
        city="Colombo",
        country="LK",
    )
    session = create_checkout_session(customer, reservation.pk, address.pk)
    order = place_order(customer, session.pk)
    payment, _ = initiate_payment(order, "webxpay")
    result = PaymentResult(
        success=True,
        provider_reference="TXN-TEST-001",
        amount_usd=order.total_usd,
        raw_response={},
    )
    record_payment_result(payment, result)
    order.refresh_from_db()
    # Create shipment to move order to processing
    create_shipment(order, carrier="DHL")
    order.refresh_from_db()
    return order


def auth_client(customer, password="StrongPass1!"):
    client = APIClient()
    res = client.post(reverse("auth-login"), {"email": customer.email, "password": password})
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return client


# ---------------------------------------------------------------------------
# create_export_record service tests
# ---------------------------------------------------------------------------

@override_settings(**WEBXPAY_SETTINGS)
class CreateExportRecordServiceTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.order = make_processing_order(self.customer, species_code="CE1")

    def test_creates_export_record_with_pending_status(self):
        record = create_export_record(
            self.order,
            destination_country="AU",
            declared_value_usd=Decimal("3050.00"),
        )
        self.assertEqual(record.compliance_status, ExportRecord.ComplianceStatus.PENDING)
        self.assertEqual(record.destination_country, "AU")
        self.assertEqual(record.declared_value_usd, Decimal("3050.00"))

    def test_stores_permit_and_declaration_numbers(self):
        record = create_export_record(
            self.order,
            destination_country="US",
            declared_value_usd=Decimal("3000.00"),
            export_permit_number="EP-2026-001",
            customs_declaration_number="CD-2026-001",
        )
        self.assertEqual(record.export_permit_number, "EP-2026-001")
        self.assertEqual(record.customs_declaration_number, "CD-2026-001")

    def test_marks_inventory_as_export_ready(self):
        create_export_record(
            self.order,
            destination_country="GB",
            declared_value_usd=Decimal("3000.00"),
            actor=self.customer.email,
        )
        inventory = self.order.checkout_session.reservation.product.inventory_item
        inventory.refresh_from_db()
        self.assertTrue(inventory.is_export_ready)

    def test_raises_if_order_not_processing_or_shipped(self):
        # confirmed order (before shipment) should fail
        species, _ = GemstoneSpecies.objects.get_or_create(
            code="CE2", defaults={"name": "Species-CE2", "common_name": "Test"}
        )
        gemstone = PhysicalGemstone.objects.create(
            species=species, acquisition_date=datetime.date.today()
        )
        inventory = InventoryItem.objects.create(
            physical_gemstone=gemstone, listing_status=ListingStatus.ACTIVE
        )
        product = Product.objects.create(
            inventory_item=inventory, price_usd=Decimal("500.00"),
            listing_status=ListingStatus.ACTIVE,
        )
        reservation = create_reservation(self.customer, product.pk)
        address = CustomerAddress.objects.get(customer=self.customer)
        session = create_checkout_session(self.customer, reservation.pk, address.pk)
        order = place_order(self.customer, session.pk)
        payment, _ = initiate_payment(order, "webxpay")
        record_payment_result(payment, PaymentResult(
            success=True, provider_reference="TXN-002",
            amount_usd=order.total_usd, raw_response={},
        ))
        order.refresh_from_db()
        # order is confirmed — no shipment yet
        with self.assertRaises(CartError):
            create_export_record(order, destination_country="US", declared_value_usd=Decimal("500.00"))

    def test_raises_on_missing_destination_country(self):
        with self.assertRaises(CartError):
            create_export_record(self.order, destination_country="", declared_value_usd=Decimal("3000.00"))

    def test_raises_on_missing_declared_value(self):
        with self.assertRaises(CartError):
            create_export_record(self.order, destination_country="US", declared_value_usd=None)

    def test_raises_on_duplicate_export_record(self):
        create_export_record(self.order, destination_country="US", declared_value_usd=Decimal("3000.00"))
        with self.assertRaises(CartError):
            create_export_record(self.order, destination_country="AU", declared_value_usd=Decimal("3000.00"))

    def test_documents_property_parses_s3_keys(self):
        record = create_export_record(
            self.order,
            destination_country="US",
            declared_value_usd=Decimal("3000.00"),
            document_s3_keys="exports/permit.pdf\nexports/declaration.pdf",
        )
        self.assertEqual(record.documents, ["exports/permit.pdf", "exports/declaration.pdf"])


# ---------------------------------------------------------------------------
# update_export_compliance service tests
# ---------------------------------------------------------------------------

@override_settings(**WEBXPAY_SETTINGS)
class UpdateExportComplianceServiceTests(TestCase):

    def setUp(self):
        self.customer = make_customer()
        self.order = make_processing_order(self.customer, species_code="UC1")
        self.record = create_export_record(
            self.order, destination_country="US", declared_value_usd=Decimal("3000.00")
        )

    def test_pending_to_cleared(self):
        record = update_export_compliance(self.record, ExportRecord.ComplianceStatus.CLEARED)
        self.assertEqual(record.compliance_status, ExportRecord.ComplianceStatus.CLEARED)

    def test_pending_to_rejected(self):
        record = update_export_compliance(self.record, ExportRecord.ComplianceStatus.REJECTED)
        self.assertEqual(record.compliance_status, ExportRecord.ComplianceStatus.REJECTED)

    def test_rejected_can_return_to_pending(self):
        update_export_compliance(self.record, ExportRecord.ComplianceStatus.REJECTED)
        record = update_export_compliance(self.record, ExportRecord.ComplianceStatus.PENDING)
        self.assertEqual(record.compliance_status, ExportRecord.ComplianceStatus.PENDING)

    def test_cleared_is_terminal(self):
        update_export_compliance(self.record, ExportRecord.ComplianceStatus.CLEARED)
        with self.assertRaises(CartError):
            update_export_compliance(self.record, ExportRecord.ComplianceStatus.REJECTED)

    def test_invalid_transition_raises(self):
        with self.assertRaises(CartError):
            update_export_compliance(self.record, "nonexistent_status")

    def test_notes_updated_on_transition(self):
        record = update_export_compliance(
            self.record, ExportRecord.ComplianceStatus.CLEARED, notes="All documents verified."
        )
        self.assertEqual(record.notes, "All documents verified.")


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

@override_settings(**WEBXPAY_SETTINGS)
class OrderExportAPITests(TestCase):

    def setUp(self):
        self.staff = make_customer("staff@example.com", is_staff=True)
        self.customer = make_customer()
        self.staff_client = auth_client(self.staff)
        self.customer_client = auth_client(self.customer)
        self.order = make_processing_order(self.customer, species_code="AP1")

    def test_staff_can_create_export_record(self):
        res = self.staff_client.post(
            reverse("order-export", args=[self.order.pk]),
            {"destination_country": "AU", "declared_value_usd": "3050.00"},
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["destination_country"], "AU")
        self.assertEqual(res.data["compliance_status"], ExportRecord.ComplianceStatus.PENDING)

    def test_non_staff_cannot_create(self):
        res = self.customer_client.post(
            reverse("order-export", args=[self.order.pk]),
            {"destination_country": "AU", "declared_value_usd": "3050.00"},
        )
        self.assertEqual(res.status_code, 403)

    def test_staff_can_get_export_record(self):
        create_export_record(self.order, destination_country="US", declared_value_usd=Decimal("3000.00"))
        res = self.staff_client.get(reverse("order-export", args=[self.order.pk]))
        self.assertEqual(res.status_code, 200)
        self.assertIn("compliance_status", res.data)

    def test_get_returns_404_when_no_record(self):
        res = self.staff_client.get(reverse("order-export", args=[self.order.pk]))
        self.assertEqual(res.status_code, 404)

    def test_staff_can_update_compliance_status(self):
        create_export_record(self.order, destination_country="US", declared_value_usd=Decimal("3000.00"))
        res = self.staff_client.put(
            reverse("order-export", args=[self.order.pk]),
            {"compliance_status": ExportRecord.ComplianceStatus.CLEARED},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["compliance_status"], ExportRecord.ComplianceStatus.CLEARED)

    def test_invalid_compliance_transition_returns_400(self):
        create_export_record(self.order, destination_country="US", declared_value_usd=Decimal("3000.00"))
        # pending → delivered is not valid
        res = self.staff_client.put(
            reverse("order-export", args=[self.order.pk]),
            {"compliance_status": "delivered"},
        )
        self.assertEqual(res.status_code, 400)

    def test_missing_compliance_status_on_put_returns_400(self):
        create_export_record(self.order, destination_country="US", declared_value_usd=Decimal("3000.00"))
        res = self.staff_client.put(reverse("order-export", args=[self.order.pk]), {})
        self.assertEqual(res.status_code, 400)

    def test_unknown_order_returns_404(self):
        res = self.staff_client.post(
            reverse("order-export", args=[99999]),
            {"destination_country": "US", "declared_value_usd": "3000.00"},
        )
        self.assertEqual(res.status_code, 404)

    def test_unauthenticated_cannot_access(self):
        res = APIClient().get(reverse("order-export", args=[self.order.pk]))
        self.assertEqual(res.status_code, 401)

    def test_non_staff_cannot_get(self):
        create_export_record(self.order, destination_country="US", declared_value_usd=Decimal("3000.00"))
        res = self.customer_client.get(reverse("order-export", args=[self.order.pk]))
        self.assertEqual(res.status_code, 403)
