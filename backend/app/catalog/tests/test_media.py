from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.utils import timezone
from catalog.models import GemstoneSpecies, Product, ProductMedia, MediaType, ValueTier
from inventory.models import InventoryItem, PhysicalGemstone


def make_product(species_code="COR"):
    species, _ = GemstoneSpecies.objects.get_or_create(
        code=species_code,
        defaults={"name": f"Species-{species_code}", "common_name": species_code},
    )
    gemstone = PhysicalGemstone.objects.create(
        species=species,
        acquisition_date=timezone.now().date(),
    )
    inventory_item = InventoryItem.objects.create(physical_gemstone=gemstone)
    return Product.objects.create(inventory_item=inventory_item, price_usd=Decimal("1000.00"))


class ProductMediaCreationTest(TestCase):

    def setUp(self):
        self.product = make_product()

    def test_media_created(self):
        m = ProductMedia.objects.create(
            product=self.product,
            s3_key="media/gems/CEY-COR-2026-000001/01.jpg",
        )
        self.assertIsNotNone(m.pk)

    def test_default_media_type_is_photo(self):
        m = ProductMedia.objects.create(product=self.product, s3_key="a/b.jpg")
        self.assertEqual(m.media_type, MediaType.PHOTO)

    def test_default_is_primary_false(self):
        m = ProductMedia.objects.create(product=self.product, s3_key="a/b.jpg")
        self.assertFalse(m.is_primary)

    def test_str_contains_gemstone_id_and_type(self):
        m = ProductMedia.objects.create(product=self.product, s3_key="a/b.jpg")
        s = str(m)
        self.assertIn(self.product.gemstone_id, s)
        self.assertIn("Photo", s)

    def test_multiple_media_per_product(self):
        ProductMedia.objects.create(product=self.product, s3_key="a/1.jpg", display_order=0)
        ProductMedia.objects.create(product=self.product, s3_key="a/2.jpg", display_order=1)
        ProductMedia.objects.create(product=self.product, s3_key="a/3.mp4", media_type=MediaType.VIDEO, display_order=2)
        self.assertEqual(self.product.media.count(), 3)


class ProductMediaPrimaryTest(TestCase):

    def setUp(self):
        self.product = make_product()

    def test_single_primary_allowed(self):
        m = ProductMedia.objects.create(
            product=self.product, s3_key="a/1.jpg", is_primary=True
        )
        self.assertTrue(m.is_primary)

    def test_two_primaries_raises_integrity_error(self):
        ProductMedia.objects.create(product=self.product, s3_key="a/1.jpg", is_primary=True)
        with self.assertRaises(IntegrityError):
            ProductMedia.objects.create(product=self.product, s3_key="a/2.jpg", is_primary=True)

    def test_primary_must_be_photo(self):
        m = ProductMedia(
            product=self.product,
            s3_key="a/cert.pdf",
            media_type=MediaType.CERTIFICATE,
            is_primary=True,
        )
        with self.assertRaises(ValidationError):
            m.clean()

    def test_non_primary_certificate_is_valid(self):
        m = ProductMedia(
            product=self.product,
            s3_key="a/cert.pdf",
            media_type=MediaType.CERTIFICATE,
            is_primary=False,
        )
        m.clean()  # should not raise

    def test_primary_photo_passes_clean(self):
        m = ProductMedia(
            product=self.product,
            s3_key="a/1.jpg",
            media_type=MediaType.PHOTO,
            is_primary=True,
        )
        m.clean()  # should not raise


class ProductMediaOrderingTest(TestCase):

    def setUp(self):
        self.product = make_product()
        ProductMedia.objects.create(product=self.product, s3_key="a/3.jpg", display_order=3)
        ProductMedia.objects.create(product=self.product, s3_key="a/1.jpg", display_order=1)
        ProductMedia.objects.create(product=self.product, s3_key="a/2.jpg", display_order=2)

    def test_media_ordered_by_display_order(self):
        keys = list(self.product.media.values_list("s3_key", flat=True))
        self.assertEqual(keys, ["a/1.jpg", "a/2.jpg", "a/3.jpg"])


class ProductMediaCascadeTest(TestCase):

    def setUp(self):
        self.product = make_product()
        ProductMedia.objects.create(product=self.product, s3_key="a/1.jpg")
        ProductMedia.objects.create(product=self.product, s3_key="a/2.jpg")

    def test_media_deleted_when_product_deleted(self):
        self.product.delete()
        self.assertEqual(ProductMedia.objects.count(), 0)


class ProductMediaTypesTest(TestCase):

    def setUp(self):
        self.product = make_product()

    def test_all_media_types_can_be_saved(self):
        for i, media_type in enumerate(MediaType):
            m = ProductMedia.objects.create(
                product=self.product,
                s3_key=f"a/{i}.file",
                media_type=media_type,
                display_order=i,
            )
            self.assertEqual(m.media_type, media_type)
