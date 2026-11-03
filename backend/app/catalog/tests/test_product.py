from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone
from django.utils.text import slugify
from catalog.models import GemstoneSpecies, Product, ValueTier
from inventory.models import InventoryItem, ListingStatus, PhysicalGemstone


def make_species(**kwargs):
    defaults = {"name": "Corundum", "common_name": "Sapphire & Ruby", "code": "COR"}
    defaults.update(kwargs)
    return GemstoneSpecies.objects.create(**defaults)


def make_gemstone(species):
    return PhysicalGemstone.objects.create(
        species=species,
        acquisition_date=timezone.now().date(),
    )


def make_inventory(gemstone):
    return InventoryItem.objects.create(physical_gemstone=gemstone)


def make_product(inventory_item, **kwargs):
    defaults = {"price_usd": Decimal("1500.00"), "value_tier": ValueTier.PREMIUM}
    defaults.update(kwargs)
    return Product.objects.create(inventory_item=inventory_item, **defaults)


class ProductCreationTest(TestCase):

    def setUp(self):
        self.species = make_species()
        self.gemstone = make_gemstone(self.species)
        self.inventory_item = make_inventory(self.gemstone)
        self.product = make_product(self.inventory_item)

    def test_product_created(self):
        self.assertIsNotNone(self.product.pk)

    def test_slug_auto_generated_from_gemstone_id(self):
        self.assertEqual(self.product.slug, slugify(self.product.gemstone_id))

    def test_slug_is_non_empty(self):
        self.assertTrue(len(self.product.slug) > 0)

    def test_default_listing_status_is_unlisted(self):
        self.assertEqual(self.product.listing_status, ListingStatus.UNLISTED)

    def test_default_value_tier_is_standard(self):
        g = make_gemstone(self.species)
        inv = make_inventory(g)
        p = Product.objects.create(inventory_item=inv, price_usd=Decimal("100.00"))
        self.assertEqual(p.value_tier, ValueTier.STANDARD)

    def test_str_contains_gemstone_id_and_price(self):
        s = str(self.product)
        self.assertIn(self.product.gemstone_id, s)
        self.assertIn("1500", s)


class ProductPropertiesTest(TestCase):

    def setUp(self):
        self.species = make_species()
        self.gemstone = make_gemstone(self.species)
        self.inventory_item = make_inventory(self.gemstone)
        self.product = make_product(self.inventory_item)

    def test_gemstone_id_property(self):
        self.assertEqual(self.product.gemstone_id, self.inventory_item.gemstone_id)

    def test_is_available_false_when_unlisted(self):
        self.assertFalse(self.product.is_available)

    def test_is_available_true_when_active(self):
        self.inventory_item.listing_status = ListingStatus.ACTIVE
        self.inventory_item.save()
        self.assertTrue(self.product.is_available)

    def test_is_available_false_when_reserved(self):
        self.inventory_item.listing_status = ListingStatus.ACTIVE
        self.inventory_item.is_reserved = True
        self.inventory_item.save()
        self.assertFalse(self.product.is_available)

    def test_is_available_false_when_sold(self):
        self.inventory_item.listing_status = ListingStatus.ACTIVE
        self.inventory_item.is_sold = True
        self.inventory_item.save()
        self.assertFalse(self.product.is_available)


class ProductOneToOneTest(TestCase):

    def setUp(self):
        self.species = make_species()
        self.gemstone = make_gemstone(self.species)
        self.inventory_item = make_inventory(self.gemstone)
        self.product = make_product(self.inventory_item)

    def test_duplicate_product_for_same_inventory_item_raises(self):
        with self.assertRaises(IntegrityError):
            Product.objects.create(
                inventory_item=self.inventory_item,
                price_usd=Decimal("999.00"),
            )

    def test_reverse_relation_from_inventory_item(self):
        self.assertEqual(self.inventory_item.product, self.product)


class ProductValueTierTest(TestCase):

    def setUp(self):
        self.species = make_species()

    def test_all_value_tiers_can_be_saved(self):
        for tier in ValueTier:
            g = make_gemstone(self.species)
            inv = make_inventory(g)
            p = Product.objects.create(
                inventory_item=inv,
                price_usd=Decimal("100.00"),
                value_tier=tier,
            )
            self.assertEqual(p.value_tier, tier)
