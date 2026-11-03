from django.db import models


class AttributeDataType(models.TextChoices):
    TEXT = "text", "Text"
    DECIMAL = "decimal", "Decimal"
    INTEGER = "integer", "Integer"
    BOOLEAN = "boolean", "Boolean"
    SELECT = "select", "Select (single choice)"
    MULTISELECT = "multiselect", "Multi-select"


class GemstoneSpecies(models.Model):
    """
    A gemstone species is the mineral species classification.
    e.g. Corundum, Spinel, Chrysoberyl, Garnet

    This is the top-level scientific classification.
    """

    name = models.CharField(max_length=100, unique=True)
    common_name = models.CharField(
        max_length=100,
        help_text="Common trade name, e.g. 'Sapphire & Ruby' for Corundum",
    )
    # Short code used in gemstone ID generation e.g. SAP, RUB, SPI
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Gemstone Species"
        verbose_name_plural = "Gemstone Species"
        ordering = ["name"]

    def __str__(self):
        return self.name


class GemstoneVariety(models.Model):
    """
    A variety is a specific named type within a species.
    e.g. Blue Sapphire, Padparadscha, Star Ruby, Alexandrite

    Varieties carry species-specific display and filtering context.
    """

    species = models.ForeignKey(
        GemstoneSpecies,
        on_delete=models.PROTECT,
        related_name="varieties",
    )
    name = models.CharField(max_length=100)
    # Short code used in gemstone ID generation e.g. BSAP, PAD, SRUB
    code = models.CharField(max_length=10)
    description = models.TextField(blank=True)
    # Typical color range description for display purposes
    typical_colors = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Gemstone Variety"
        verbose_name_plural = "Gemstone Varieties"
        ordering = ["species__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["species", "name"], name="unique_variety_per_species"
            ),
            models.UniqueConstraint(
                fields=["species", "code"], name="unique_variety_code_per_species"
            ),
        ]

    def __str__(self):
        return f"{self.species.name} — {self.name}"


class GemstoneAttributeDefinition(models.Model):
    """
    Defines an attribute that applies to a specific gemstone species.

    Examples:
      - Corundum: Color, Hue, Tone, Saturation, Clarity, Cut, Shape
      - Chrysoberyl: Chatoyancy, Colour Change Description
      - Garnet: Variety Type, Colour Change Description

    Attribute definitions are species-scoped. The same attribute name
    (e.g. "Color") can exist for multiple species independently.
    """

    species = models.ForeignKey(
        GemstoneSpecies,
        on_delete=models.PROTECT,
        related_name="attribute_definitions",
    )
    name = models.CharField(max_length=100)
    # Internal key used in code e.g. "color", "chatoyancy_strength"
    key = models.SlugField(max_length=100)
    data_type = models.CharField(
        max_length=20,
        choices=AttributeDataType.choices,
        default=AttributeDataType.TEXT,
    )
    unit = models.CharField(
        max_length=20,
        blank=True,
        help_text="Optional unit of measurement, e.g. 'ct' for carat weight",
    )
    is_required = models.BooleanField(
        default=False,
        help_text="Whether this attribute must be provided for every gemstone of this species",
    )
    is_filterable = models.BooleanField(
        default=False,
        help_text="Whether this attribute appears as a filter in the catalog",
    )
    is_displayed = models.BooleanField(
        default=True,
        help_text="Whether this attribute is shown on the product page",
    )
    display_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Controls display order on product page and filters",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Attribute Definition"
        verbose_name_plural = "Attribute Definitions"
        ordering = ["species__name", "display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["species", "key"],
                name="unique_attribute_key_per_species",
            )
        ]

    def __str__(self):
        return f"{self.species.name} — {self.name}"


class GemstoneAttributeOption(models.Model):
    """
    Predefined options for SELECT and MULTISELECT attribute definitions.

    Example:
      - Attribute: "Shape"
      - Options: Round, Oval, Cushion, Pear, Emerald Cut, Cabochon, ...
    """

    attribute = models.ForeignKey(
        GemstoneAttributeDefinition,
        on_delete=models.CASCADE,
        related_name="options",
    )
    value = models.CharField(max_length=100)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Attribute Option"
        verbose_name_plural = "Attribute Options"
        ordering = ["attribute", "display_order", "value"]
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "value"],
                name="unique_option_value_per_attribute",
            )
        ]

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


# ---------------------------------------------------------------------------
# Product & catalog model — module 1.8
# ---------------------------------------------------------------------------
from django.utils.text import slugify
from inventory.models import InventoryItem, ListingStatus


class ValueTier(models.TextChoices):
    """
    Broad value classification used for shipping rules, display badges,
    and insurance thresholds. Thresholds are configurable via admin
    (see Phase 5 shipping configuration).
    """
    STANDARD = "standard", "Standard"
    PREMIUM = "premium", "Premium"
    LUXURY = "luxury", "Luxury"
    ULTRA_LUXURY = "ultra_luxury", "Ultra Luxury"


class Product(models.Model):
    """
    Customer-facing product record for a physical gemstone.

    One InventoryItem has exactly one Product.
    Product carries the public pricing, value tier, slug, and listing
    status that the storefront consumes. The underlying gemological
    and inventory records remain in their own models.

    listing_status mirrors InventoryItem.listing_status — the inventory
    layer is the source of truth; this field drives catalog visibility.
    """

    inventory_item = models.OneToOneField(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="product",
    )

    # Public pricing — in USD (international storefront)
    price_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Public selling price in USD",
    )

    # Value tier — drives shipping rules and display badges
    value_tier = models.CharField(
        max_length=20,
        choices=ValueTier.choices,
        default=ValueTier.STANDARD,
    )

    # URL slug — auto-generated from gemstone ID, editable for SEO
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    # Short marketing headline shown on product cards
    headline = models.CharField(
        max_length=200,
        blank=True,
        help_text="Short marketing headline, e.g. 'Unheated Royal Blue Sapphire'",
    )

    # Long-form description for the product detail page
    description = models.TextField(blank=True)

    # Mirrors InventoryItem.listing_status — updated by inventory services
    listing_status = models.CharField(
        max_length=20,
        choices=ListingStatus.choices,
        default=ListingStatus.UNLISTED,
    )

    # SEO metadata
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.inventory_item.gemstone_id} — {self.get_value_tier_display()} — ${self.price_usd}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.inventory_item.gemstone_id)
        super().save(*args, **kwargs)

    @property
    def gemstone_id(self) -> str:
        return self.inventory_item.gemstone_id

    @property
    def is_available(self) -> bool:
        return self.inventory_item.is_available


# ---------------------------------------------------------------------------
# Media model — module 1.9
# ---------------------------------------------------------------------------
from django.core.exceptions import ValidationError


class MediaType(models.TextChoices):
    PHOTO = "photo", "Photo"
    VIDEO = "video", "Video"
    CERTIFICATE = "certificate", "Certificate"
    GRADING_REPORT = "grading_report", "Grading Report"
    OTHER = "other", "Other"


class ProductMedia(models.Model):
    """
    A media asset associated with a product.

    s3_key stores the S3 object key only (e.g. 'media/gems/CEY-COR-2026-000001/01.jpg').
    Full signed URLs are generated at request time in the API layer (module 2.4).

    Ordering is explicit via display_order. Exactly one item per product
    may be marked is_primary=True — enforced in clean() and via a partial
    unique index.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="media",
    )
    media_type = models.CharField(
        max_length=20,
        choices=MediaType.choices,
        default=MediaType.PHOTO,
    )
    s3_key = models.CharField(
        max_length=500,
        help_text="S3 object key, e.g. 'media/gems/CEY-COR-2026-000001/01.jpg'",
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="Accessibility alt text for images",
    )
    display_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Lower numbers appear first",
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary photo shown on product cards and as the hero image",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Product Media"
        verbose_name_plural = "Product Media"
        ordering = ["product", "display_order", "created_at"]
        constraints = [
            # Only one primary media item per product — enforced at DB level
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_primary=True),
                name="unique_primary_media_per_product",
            )
        ]

    def __str__(self):
        return f"{self.product.gemstone_id} | {self.get_media_type_display()} | order={self.display_order}"

    def clean(self):
        if self.is_primary and self.media_type != MediaType.PHOTO:
            raise ValidationError("Only a photo can be marked as the primary media item.")
