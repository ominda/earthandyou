from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from catalog.models import GemstoneSpecies, GemstoneVariety, Product, ProductMedia, MediaType, ValueTier
from inventory.models import InventoryItem, ListingStatus, PhysicalGemstone

LIST_URL = "/api/v1/catalog/products/"


def make_product(species, variety=None, price=Decimal("1000.00"), listing_status=ListingStatus.ACTIVE, value_tier=ValueTier.STANDARD):
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
        headline="Test Gem",
    )


class ProductListAPITest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.corundum = GemstoneSpecies.objects.create(name="Corundum", common_name="Sapphire", code="COR")
        self.spinel = GemstoneSpecies.objects.create(name="Spinel", common_name="Spinel", code="SPI")
        self.variety = GemstoneVariety.objects.create(species=self.corundum, name="Blue Sapphire", code="BSAP")
        self.p1 = make_product(self.corundum, variety=self.variety, price=Decimal("2000.00"), value_tier=ValueTier.PREMIUM)
        self.p2 = make_product(self.spinel, price=Decimal("500.00"))

    def test_returns_200(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)

    def test_returns_active_products(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.data["count"], 2)

    def test_unlisted_product_excluded(self):
        make_product(self.corundum, listing_status=ListingStatus.UNLISTED)
        response = self.client.get(LIST_URL)
        self.assertEqual(response.data["count"], 2)

    def test_response_shape(self):
        response = self.client.get(LIST_URL)
        item = response.data["results"][0]
        for field in ["id", "gemstone_id", "slug", "species", "species_code", "variety",
                      "headline", "price_usd", "value_tier", "listing_status", "is_available", "primary_media"]:
            self.assertIn(field, item)

    def test_variety_name_present(self):
        response = self.client.get(LIST_URL)
        results = {r["gemstone_id"]: r for r in response.data["results"]}
        self.assertEqual(results[self.p1.gemstone_id]["variety"], "Blue Sapphire")
        self.assertIsNone(results[self.p2.gemstone_id]["variety"])

    def test_primary_media_returned(self):
        ProductMedia.objects.create(
            product=self.p1,
            s3_key="media/gems/test/01.jpg",
            is_primary=True,
            media_type=MediaType.PHOTO,
        )
        response = self.client.get(LIST_URL)
        results = {r["gemstone_id"]: r for r in response.data["results"]}
        self.assertEqual(results[self.p1.gemstone_id]["primary_media"]["s3_key"], "media/gems/test/01.jpg")
        self.assertIsNone(results[self.p2.gemstone_id]["primary_media"])

    def test_pagination_present(self):
        response = self.client.get(LIST_URL)
        for key in ["count", "next", "previous", "results"]:
            self.assertIn(key, response.data)


class ProductListFilterTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.corundum = GemstoneSpecies.objects.create(name="Corundum", common_name="Sapphire", code="COR")
        self.spinel = GemstoneSpecies.objects.create(name="Spinel", common_name="Spinel", code="SPI")
        self.variety = GemstoneVariety.objects.create(species=self.corundum, name="Blue Sapphire", code="BSAP")
        self.p_cor = make_product(self.corundum, variety=self.variety, price=Decimal("3000.00"), value_tier=ValueTier.LUXURY)
        self.p_spi = make_product(self.spinel, price=Decimal("800.00"))

    def test_filter_by_species(self):
        response = self.client.get(LIST_URL, {"species": "COR"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["species_code"], "COR")

    def test_filter_by_species_case_insensitive(self):
        response = self.client.get(LIST_URL, {"species": "cor"})
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_value_tier(self):
        response = self.client.get(LIST_URL, {"value_tier": "luxury"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["value_tier"], "luxury")

    def test_filter_price_min(self):
        response = self.client.get(LIST_URL, {"price_min": "1000"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["gemstone_id"], self.p_cor.gemstone_id)

    def test_filter_price_max(self):
        response = self.client.get(LIST_URL, {"price_max": "1000"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["gemstone_id"], self.p_spi.gemstone_id)

    def test_filter_price_range(self):
        response = self.client.get(LIST_URL, {"price_min": "500", "price_max": "1000"})
        self.assertEqual(response.data["count"], 1)

    def test_filter_available_true(self):
        # Reserve p_cor
        self.p_cor.inventory_item.is_reserved = True
        self.p_cor.inventory_item.save()
        response = self.client.get(LIST_URL, {"available": "true"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["gemstone_id"], self.p_spi.gemstone_id)

    def test_filter_by_variety(self):
        response = self.client.get(LIST_URL, {"variety": "Blue Sapphire"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["variety"], "Blue Sapphire")
