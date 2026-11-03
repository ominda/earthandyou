from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from catalog.models import GemstoneSpecies, GemstoneVariety, Product, ValueTier
from inventory.models import InventoryItem, ListingStatus, PhysicalGemstone
from certification.models import (
    Laboratory, LaboratoryType, CertificationReport,
    NaturalStatus, TreatmentStatus,
)

LIST_URL = "/api/v1/catalog/products/"


def make_lab():
    return Laboratory.objects.get_or_create(
        code="NGJA",
        defaults={"name": "NGJA", "laboratory_type": LaboratoryType.LOCAL},
    )[0]


def make_product(species, variety=None, price=Decimal("1000.00"),
                 value_tier=ValueTier.STANDARD, headline="Test Gem",
                 listing_status=ListingStatus.ACTIVE):
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
        price_usd=price,
        value_tier=value_tier,
        listing_status=listing_status,
        headline=headline,
    )


def add_report(product, treatment=TreatmentStatus.UNHEATED,
               natural=NaturalStatus.NATURAL, origin="Sri Lanka",
               carat=Decimal("2.50"), is_active=True):
    lab = make_lab()
    return CertificationReport.objects.create(
        physical_gemstone=product.inventory_item.physical_gemstone,
        laboratory=lab,
        report_number=f"RPT-{product.pk}-{treatment}",
        issue_date=timezone.now().date(),
        treatment_status=treatment,
        natural_status=natural,
        origin_country=origin,
        reported_carat_weight=carat,
        is_active=is_active,
    )


class SearchFilterTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.corundum = GemstoneSpecies.objects.create(name="Corundum", common_name="Sapphire", code="COR")
        self.spinel = GemstoneSpecies.objects.create(name="Spinel", common_name="Spinel", code="SPI")
        self.variety = GemstoneVariety.objects.create(species=self.corundum, name="Blue Sapphire", code="BSAP")
        self.p1 = make_product(self.corundum, variety=self.variety, headline="Unheated Royal Blue Sapphire")
        self.p2 = make_product(self.spinel, headline="Red Spinel Burma")

    def test_search_by_headline(self):
        response = self.client.get(LIST_URL, {"search": "Royal Blue"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["gemstone_id"], self.p1.gemstone_id)

    def test_search_by_species_name(self):
        response = self.client.get(LIST_URL, {"search": "Spinel"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["gemstone_id"], self.p2.gemstone_id)

    def test_search_by_variety_name(self):
        response = self.client.get(LIST_URL, {"search": "Blue Sapphire"})
        self.assertEqual(response.data["count"], 1)

    def test_search_by_gemstone_id(self):
        response = self.client.get(LIST_URL, {"search": self.p1.gemstone_id})
        self.assertEqual(response.data["count"], 1)

    def test_search_no_match_returns_empty(self):
        response = self.client.get(LIST_URL, {"search": "Emerald"})
        self.assertEqual(response.data["count"], 0)


class TreatmentFilterTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.species = GemstoneSpecies.objects.create(name="Corundum", common_name="Sapphire", code="COR")
        self.p_unheated = make_product(self.species, headline="Unheated")
        self.p_heated = make_product(self.species, headline="Heated")
        add_report(self.p_unheated, treatment=TreatmentStatus.UNHEATED)
        add_report(self.p_heated, treatment=TreatmentStatus.HEATED)

    def test_filter_unheated(self):
        response = self.client.get(LIST_URL, {"treatment": "unheated"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["gemstone_id"], self.p_unheated.gemstone_id)

    def test_filter_heated(self):
        response = self.client.get(LIST_URL, {"treatment": "heated"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["gemstone_id"], self.p_heated.gemstone_id)

    def test_inactive_report_not_matched(self):
        p = make_product(self.species, headline="Inactive cert")
        add_report(p, treatment=TreatmentStatus.UNHEATED, is_active=False)
        response = self.client.get(LIST_URL, {"treatment": "unheated"})
        # Only p_unheated should match — inactive report excluded
        self.assertEqual(response.data["count"], 1)


class NaturalStatusFilterTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.species = GemstoneSpecies.objects.create(name="Corundum", common_name="Sapphire", code="COR")
        self.p_natural = make_product(self.species)
        self.p_synthetic = make_product(self.species)
        add_report(self.p_natural, natural=NaturalStatus.NATURAL)
        add_report(self.p_synthetic, treatment=TreatmentStatus.UNKNOWN, natural=NaturalStatus.SYNTHETIC)

    def test_filter_natural(self):
        response = self.client.get(LIST_URL, {"natural_status": "natural"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["gemstone_id"], self.p_natural.gemstone_id)

    def test_filter_synthetic(self):
        response = self.client.get(LIST_URL, {"natural_status": "synthetic"})
        self.assertEqual(response.data["count"], 1)


class OriginFilterTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.species = GemstoneSpecies.objects.create(name="Corundum", common_name="Sapphire", code="COR")
        self.p_sl = make_product(self.species)
        self.p_burma = make_product(self.species)
        add_report(self.p_sl, origin="Sri Lanka")
        add_report(self.p_burma, origin="Myanmar")

    def test_filter_by_origin(self):
        response = self.client.get(LIST_URL, {"origin": "Sri Lanka"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["gemstone_id"], self.p_sl.gemstone_id)

    def test_filter_origin_case_insensitive(self):
        response = self.client.get(LIST_URL, {"origin": "sri lanka"})
        self.assertEqual(response.data["count"], 1)

    def test_filter_origin_partial_match(self):
        response = self.client.get(LIST_URL, {"origin": "Lanka"})
        self.assertEqual(response.data["count"], 1)


class CaratFilterTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.species = GemstoneSpecies.objects.create(name="Corundum", common_name="Sapphire", code="COR")
        self.p_small = make_product(self.species)
        self.p_large = make_product(self.species)
        add_report(self.p_small, carat=Decimal("1.20"))
        add_report(self.p_large, carat=Decimal("5.80"))

    def test_carat_min(self):
        response = self.client.get(LIST_URL, {"carat_min": "3.00"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["gemstone_id"], self.p_large.gemstone_id)

    def test_carat_max(self):
        response = self.client.get(LIST_URL, {"carat_max": "2.00"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["gemstone_id"], self.p_small.gemstone_id)

    def test_carat_range(self):
        response = self.client.get(LIST_URL, {"carat_min": "1.00", "carat_max": "2.00"})
        self.assertEqual(response.data["count"], 1)


class OrderingFilterTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.species = GemstoneSpecies.objects.create(name="Corundum", common_name="Sapphire", code="COR")
        self.p_cheap = make_product(self.species, price=Decimal("500.00"))
        self.p_mid = make_product(self.species, price=Decimal("1500.00"))
        self.p_expensive = make_product(self.species, price=Decimal("3000.00"))

    def test_order_by_price_asc(self):
        response = self.client.get(LIST_URL, {"ordering": "price"})
        prices = [float(r["price_usd"]) for r in response.data["results"]]
        self.assertEqual(prices, sorted(prices))

    def test_order_by_price_desc(self):
        response = self.client.get(LIST_URL, {"ordering": "-price"})
        prices = [float(r["price_usd"]) for r in response.data["results"]]
        self.assertEqual(prices, sorted(prices, reverse=True))
