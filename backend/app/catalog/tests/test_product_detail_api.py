from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from catalog.models import GemstoneSpecies, GemstoneVariety, Product, ProductMedia, MediaType, ValueTier
from inventory.models import InventoryItem, ListingStatus, PhysicalGemstone
from certification.models import Laboratory, LaboratoryType, CertificationReport, NaturalStatus, TreatmentStatus, ProvenanceRecord, ProvenanceConfidence


def make_lab():
    return Laboratory.objects.create(
        name="NGJA",
        code="NGJA",
        laboratory_type=LaboratoryType.LOCAL,
    )


def make_product(species, variety=None, listing_status=ListingStatus.ACTIVE):
    gemstone = PhysicalGemstone.objects.create(
        species=species,
        variety=variety,
        acquisition_date=timezone.now().date(),
    )
    inv = InventoryItem.objects.create(
        physical_gemstone=gemstone,
        listing_status=listing_status,
    )
    return Product.objects.create(
        inventory_item=inv,
        price_usd=Decimal("2500.00"),
        value_tier=ValueTier.PREMIUM,
        listing_status=listing_status,
        headline="Unheated Blue Sapphire",
        description="A fine Ceylon sapphire.",
    )


class ProductDetailAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.species = GemstoneSpecies.objects.create(name="Corundum", common_name="Sapphire", code="COR")
        self.variety = GemstoneVariety.objects.create(species=self.species, name="Blue Sapphire", code="BSAP")
        self.product = make_product(self.species, variety=self.variety)
        self.url = f"/api/v1/catalog/products/{self.product.slug}/"

    def test_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_returns_404_for_unknown_slug(self):
        response = self.client.get("/api/v1/catalog/products/does-not-exist/")
        self.assertEqual(response.status_code, 404)

    def test_unlisted_product_returns_404(self):
        unlisted = make_product(self.species, listing_status=ListingStatus.UNLISTED)
        response = self.client.get(f"/api/v1/catalog/products/{unlisted.slug}/")
        self.assertEqual(response.status_code, 404)

    def test_response_shape(self):
        response = self.client.get(self.url)
        data = response.data
        for field in [
            "id", "gemstone_id", "slug", "species", "species_code", "variety",
            "headline", "description", "price_usd", "value_tier", "listing_status",
            "is_available", "meta_title", "meta_description",
            "media", "certification_reports", "provenance",
        ]:
            self.assertIn(field, data)

    def test_gemstone_id_and_species_correct(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["gemstone_id"], self.product.gemstone_id)
        self.assertEqual(response.data["species"], "Corundum")
        self.assertEqual(response.data["species_code"], "COR")
        self.assertEqual(response.data["variety"], "Blue Sapphire")

    def test_no_provenance_returns_null(self):
        response = self.client.get(self.url)
        self.assertIsNone(response.data["provenance"])

    def test_no_certification_returns_empty_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["certification_reports"], [])

    def test_media_list_empty_by_default(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data["media"], [])


class ProductDetailMediaTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.species = GemstoneSpecies.objects.create(name="Corundum", common_name="Sapphire", code="COR")
        self.product = make_product(self.species)
        self.url = f"/api/v1/catalog/products/{self.product.slug}/"
        ProductMedia.objects.create(
            product=self.product, s3_key="media/01.jpg", media_type=MediaType.PHOTO,
            is_primary=True, display_order=0,
        )
        ProductMedia.objects.create(
            product=self.product, s3_key="media/cert.pdf", media_type=MediaType.CERTIFICATE,
            display_order=1,
        )

    def test_all_media_returned(self):
        response = self.client.get(self.url)
        self.assertEqual(len(response.data["media"]), 2)

    def test_media_fields_present(self):
        response = self.client.get(self.url)
        item = response.data["media"][0]
        for field in ["id", "media_type", "s3_key", "alt_text", "display_order", "is_primary"]:
            self.assertIn(field, item)

    def test_media_ordered_by_display_order(self):
        response = self.client.get(self.url)
        orders = [m["display_order"] for m in response.data["media"]]
        self.assertEqual(orders, sorted(orders))


class ProductDetailCertificationTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.species = GemstoneSpecies.objects.create(name="Corundum", common_name="Sapphire", code="COR")
        self.product = make_product(self.species)
        self.lab = make_lab()
        self.report = CertificationReport.objects.create(
            physical_gemstone=self.product.inventory_item.physical_gemstone,
            laboratory=self.lab,
            report_number="NGJA-2026-001",
            issue_date=timezone.now().date(),
            natural_status=NaturalStatus.NATURAL,
            treatment_status=TreatmentStatus.UNHEATED,
            origin_country="Sri Lanka",
            is_primary=True,
        )
        self.url = f"/api/v1/catalog/products/{self.product.slug}/"

    def test_certification_report_returned(self):
        response = self.client.get(self.url)
        self.assertEqual(len(response.data["certification_reports"]), 1)

    def test_certification_fields_present(self):
        response = self.client.get(self.url)
        report = response.data["certification_reports"][0]
        for field in [
            "id", "laboratory_name", "laboratory_code", "report_number",
            "report_type", "issue_date", "natural_status", "treatment_status",
            "origin_country", "verification_url", "is_primary",
        ]:
            self.assertIn(field, report)

    def test_inactive_report_excluded(self):
        self.report.is_active = False
        self.report.save()
        response = self.client.get(self.url)
        self.assertEqual(response.data["certification_reports"], [])


class ProductDetailProvenanceTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.species = GemstoneSpecies.objects.create(name="Corundum", common_name="Sapphire", code="COR")
        self.product = make_product(self.species)
        self.provenance = ProvenanceRecord.objects.create(
            physical_gemstone=self.product.inventory_item.physical_gemstone,
            confidence=ProvenanceConfidence.DOCUMENTED,
            origin_country="Sri Lanka",
            source_region="Ratnapura District",
            customer_description="Sourced from the gem fields of Ratnapura.",
        )
        self.url = f"/api/v1/catalog/products/{self.product.slug}/"

    def test_provenance_returned(self):
        response = self.client.get(self.url)
        self.assertIsNotNone(response.data["provenance"])

    def test_provenance_fields_present(self):
        response = self.client.get(self.url)
        prov = response.data["provenance"]
        for field in ["confidence", "origin_country", "source_region", "mine_locality", "customer_description"]:
            self.assertIn(field, prov)

    def test_internal_fields_not_exposed(self):
        response = self.client.get(self.url)
        prov = response.data["provenance"]
        for field in ["acquisition_source", "acquisition_notes", "internal_notes", "supporting_document_s3_keys"]:
            self.assertNotIn(field, prov)

    def test_provenance_values_correct(self):
        response = self.client.get(self.url)
        prov = response.data["provenance"]
        self.assertEqual(prov["origin_country"], "Sri Lanka")
        self.assertEqual(prov["confidence"], "documented")
