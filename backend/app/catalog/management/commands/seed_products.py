"""
Seed realistic product test data for Earth & You.

Creates 6 products covering different species, value tiers, and states.
Depends on: seed_gemstone_species, seed_laboratories (run those first).

Usage:
    python manage.py seed_products
    python manage.py seed_products --clear
"""
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone

from catalog.models import GemstoneSpecies, GemstoneVariety, Product, ProductMedia, ValueTier
from certification.models import (
    Laboratory, CertificationReport, ReportType,
    NaturalStatus, TreatmentStatus, VerificationStatus, ProvenanceRecord, ProvenanceConfidence,
)
from inventory.models import (
    PhysicalGemstone, InventoryItem, InventorySource,
    CustodyStatus, ListingStatus, GemstoneLifecycleState,
)


PRODUCTS = [
    {
        "species_code": "COR",
        "variety_code": "BSAP",
        "lifecycle_state": GemstoneLifecycleState.LISTED,
        "acquisition_date": datetime.date(2024, 3, 15),
        "listing_status": ListingStatus.ACTIVE,
        "value_tier": ValueTier.LUXURY,
        "price_usd": "4800.00",
        "headline": "Unheated Royal Blue Sapphire — Ceylon",
        "description": (
            "A stunning unheated blue sapphire from the gem fields of Ratnapura, Sri Lanka. "
            "Deep royal blue with excellent transparency and a well-proportioned oval cut. "
            "Certified unheated by GRS with Sri Lankan origin confirmation."
        ),
        "cert": {
            "lab_code": "GRS",
            "report_number": "GRS2024-031201",
            "report_type": ReportType.ORIGIN_TREATMENT,
            "issue_date": datetime.date(2024, 4, 10),
            "natural_status": NaturalStatus.NATURAL,
            "treatment_status": TreatmentStatus.UNHEATED,
            "origin_country": "Sri Lanka",
            "reported_carat_weight": "3.42",
            "reported_dimensions": "9.81 x 7.63 x 5.12 mm",
            "verification_status": VerificationStatus.VERIFIED,
        },
        "provenance": {
            "confidence": ProvenanceConfidence.VERIFIED,
            "origin_country": "Sri Lanka",
            "source_region": "Ratnapura District",
            "mine_locality": "Elahera",
            "customer_description": (
                "Sourced directly from the Ratnapura gem fields, the historic heart of Ceylon's "
                "sapphire trade. Origin confirmed by GRS laboratory report."
            ),
        },
        "media": [
            {"s3_key": "https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?w=600&q=80", "alt_text": "Royal blue sapphire oval cut, face-up", "is_primary": True, "display_order": 0},
            {"s3_key": "https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?w=600&q=80", "alt_text": "Royal blue sapphire side profile", "is_primary": False, "display_order": 1},
        ],
    },
    {
        "species_code": "COR",
        "variety_code": "PAD",
        "lifecycle_state": GemstoneLifecycleState.LISTED,
        "acquisition_date": datetime.date(2024, 5, 2),
        "listing_status": ListingStatus.ACTIVE,
        "value_tier": ValueTier.ULTRA_LUXURY,
        "price_usd": "18500.00",
        "headline": "Padparadscha Sapphire — Pinkish-Orange, Unheated",
        "description": (
            "An exceptionally rare padparadscha sapphire displaying the coveted pinkish-orange "
            "hue that defines this variety. Unheated and natural, certified by GIA. "
            "A collector-grade stone from Sri Lanka's finest deposits."
        ),
        "cert": {
            "lab_code": "GIA",
            "report_number": "2211093847",
            "report_type": ReportType.ORIGIN_TREATMENT,
            "issue_date": datetime.date(2024, 6, 1),
            "natural_status": NaturalStatus.NATURAL,
            "treatment_status": TreatmentStatus.UNHEATED,
            "origin_country": "Sri Lanka",
            "reported_carat_weight": "2.18",
            "reported_dimensions": "8.10 x 6.95 x 4.33 mm",
            "verification_status": VerificationStatus.VERIFIED,
        },
        "provenance": {
            "confidence": ProvenanceConfidence.VERIFIED,
            "origin_country": "Sri Lanka",
            "source_region": "Ratnapura District",
            "customer_description": (
                "Origin confirmed by GIA. Padparadscha sapphires of this quality and colour "
                "balance are among the rarest gemstones in the world."
            ),
        },
        "media": [
            {"s3_key": "https://images.unsplash.com/photo-1611591437281-460bfbe1220a?w=600&q=80", "alt_text": "Padparadscha sapphire oval, pinkish-orange", "is_primary": True, "display_order": 0},
        ],
    },
    {
        "species_code": "CHR",
        "variety_code": "ALE",
        "lifecycle_state": GemstoneLifecycleState.LISTED,
        "acquisition_date": datetime.date(2024, 1, 20),
        "listing_status": ListingStatus.ACTIVE,
        "value_tier": ValueTier.LUXURY,
        "price_usd": "7200.00",
        "headline": "Ceylon Alexandrite — Strong Colour Change",
        "description": (
            "A fine alexandrite from Sri Lanka exhibiting a strong colour change from "
            "bluish-green in daylight to purplish-red under incandescent light. "
            "Natural and untreated, certified by NGJA."
        ),
        "cert": {
            "lab_code": "NGJA",
            "report_number": "NGJA-2024-00412",
            "report_type": ReportType.IDENTIFICATION,
            "issue_date": datetime.date(2024, 2, 14),
            "natural_status": NaturalStatus.NATURAL,
            "treatment_status": TreatmentStatus.NO_INDICATIONS,
            "origin_country": "Sri Lanka",
            "reported_carat_weight": "1.87",
            "reported_dimensions": "7.42 x 6.10 x 4.55 mm",
            "verification_status": VerificationStatus.UNVERIFIED,
        },
        "provenance": {
            "confidence": ProvenanceConfidence.DOCUMENTED,
            "origin_country": "Sri Lanka",
            "source_region": "Kandy District",
            "customer_description": (
                "Acquired directly from a licensed Sri Lankan gem dealer with documented "
                "purchase records. NGJA certified natural alexandrite."
            ),
        },
        "media": [
            {"s3_key": "https://images.unsplash.com/photo-1617038220319-276d3cfab638?w=600&q=80", "alt_text": "Alexandrite in daylight — bluish-green", "is_primary": True, "display_order": 0},
            {"s3_key": "https://images.unsplash.com/photo-1617038220319-276d3cfab638?w=600&q=80", "alt_text": "Alexandrite under incandescent light — purplish-red", "is_primary": False, "display_order": 1},
        ],
    },
    {
        "species_code": "SPI",
        "variety_code": "RSPI",
        "lifecycle_state": GemstoneLifecycleState.LISTED,
        "acquisition_date": datetime.date(2024, 7, 8),
        "listing_status": ListingStatus.ACTIVE,
        "value_tier": ValueTier.PREMIUM,
        "price_usd": "2950.00",
        "headline": "Vivid Red Ceylon Spinel — Unheated",
        "description": (
            "A vivid red spinel from Sri Lanka with excellent saturation and transparency. "
            "Historically confused with ruby, fine red spinel is increasingly sought after "
            "by collectors. Unheated and natural."
        ),
        "cert": {
            "lab_code": "NGJA",
            "report_number": "NGJA-2024-00891",
            "report_type": ReportType.IDENTIFICATION,
            "issue_date": datetime.date(2024, 8, 5),
            "natural_status": NaturalStatus.NATURAL,
            "treatment_status": TreatmentStatus.UNHEATED,
            "origin_country": "Sri Lanka",
            "reported_carat_weight": "2.63",
            "reported_dimensions": "8.55 x 7.20 x 4.80 mm",
            "verification_status": VerificationStatus.UNVERIFIED,
        },
        "provenance": {
            "confidence": ProvenanceConfidence.SELLER_PROVIDED,
            "origin_country": "Sri Lanka",
            "source_region": "Ratnapura District",
            "customer_description": (
                "Origin stated by the seller as Ratnapura, Sri Lanka. "
                "NGJA certified natural red spinel."
            ),
        },
        "media": [
            {"s3_key": "https://images.unsplash.com/photo-1573408301185-9519f94816b5?w=600&q=80", "alt_text": "Vivid red spinel oval cut", "is_primary": True, "display_order": 0},
        ],
    },
    {
        "species_code": "CHR",
        "variety_code": "CAT",
        "lifecycle_state": GemstoneLifecycleState.LISTED,
        "acquisition_date": datetime.date(2024, 2, 28),
        "listing_status": ListingStatus.ACTIVE,
        "value_tier": ValueTier.PREMIUM,
        "price_usd": "3400.00",
        "headline": "Cat's Eye Chrysoberyl — Sharp Eye, Honey Yellow",
        "description": (
            "A fine cat's eye chrysoberyl cabochon displaying a sharp, well-centred chatoyant "
            "band — the 'eye'. Honey yellow body colour with excellent translucency. "
            "One of Sri Lanka's most prized phenomenal gemstones."
        ),
        "cert": {
            "lab_code": "NGJA",
            "report_number": "NGJA-2024-00234",
            "report_type": ReportType.IDENTIFICATION,
            "issue_date": datetime.date(2024, 3, 20),
            "natural_status": NaturalStatus.NATURAL,
            "treatment_status": TreatmentStatus.NO_INDICATIONS,
            "origin_country": "Sri Lanka",
            "reported_carat_weight": "4.15",
            "reported_dimensions": "9.20 x 8.80 x 5.60 mm",
            "verification_status": VerificationStatus.UNVERIFIED,
        },
        "provenance": {
            "confidence": ProvenanceConfidence.DOCUMENTED,
            "origin_country": "Sri Lanka",
            "source_region": "Matale District",
            "customer_description": (
                "Sourced from the Matale District, a known source of fine cat's eye chrysoberyl "
                "in Sri Lanka. Accompanied by purchase documentation."
            ),
        },
        "media": [
            {"s3_key": "https://images.unsplash.com/photo-1589656966895-2f33e7653819?w=600&q=80", "alt_text": "Cat's eye chrysoberyl cabochon showing chatoyancy", "is_primary": True, "display_order": 0},
        ],
    },
    {
        "species_code": "COR",
        "variety_code": "PSAP",
        "lifecycle_state": GemstoneLifecycleState.LISTED,
        "acquisition_date": datetime.date(2024, 9, 10),
        "listing_status": ListingStatus.ACTIVE,
        "value_tier": ValueTier.STANDARD,
        "price_usd": "1250.00",
        "headline": "Pink Sapphire — Vivid Pink, Ceylon",
        "description": (
            "A bright vivid pink sapphire from Sri Lanka with excellent clarity and a "
            "well-proportioned cushion cut. A beautiful and accessible entry into "
            "Ceylon's finest gemstones."
        ),
        "cert": {
            "lab_code": "NGJA",
            "report_number": "NGJA-2024-01102",
            "report_type": ReportType.IDENTIFICATION,
            "issue_date": datetime.date(2024, 10, 1),
            "natural_status": NaturalStatus.NATURAL,
            "treatment_status": TreatmentStatus.HEATED,
            "origin_country": "Sri Lanka",
            "reported_carat_weight": "1.54",
            "reported_dimensions": "7.10 x 6.40 x 4.20 mm",
            "verification_status": VerificationStatus.UNVERIFIED,
        },
        "provenance": {
            "confidence": ProvenanceConfidence.SELLER_PROVIDED,
            "origin_country": "Sri Lanka",
            "source_region": "Ratnapura District",
            "customer_description": "Natural pink sapphire from Sri Lanka, NGJA certified.",
        },
        "media": [
            {"s3_key": "https://images.unsplash.com/photo-1598560917807-1bae44bd2be8?w=600&q=80", "alt_text": "Vivid pink sapphire cushion cut", "is_primary": True, "display_order": 0},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the database with realistic product test data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove previously seeded products before re-seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            headlines = [p["headline"] for p in PRODUCTS]
            report_numbers = [p["cert"]["report_number"] for p in PRODUCTS]
            deleted = Product.objects.filter(headline__in=headlines).count()
            for product in Product.objects.filter(headline__in=headlines):
                inv = product.inventory_item
                product.delete()
                inv.delete()
            CertificationReport.objects.filter(report_number__in=report_numbers).delete()
            self.stdout.write(self.style.WARNING(f"Removed {deleted} existing seeded products."))

        created = 0
        skipped = 0

        for data in PRODUCTS:
            if Product.objects.filter(headline=data["headline"]).exists():
                skipped += 1
                continue

            species = GemstoneSpecies.objects.get(code=data["species_code"])
            variety = GemstoneVariety.objects.get(species=species, code=data["variety_code"])
            lab = Laboratory.objects.get(code=data["cert"]["lab_code"])

            # 1. PhysicalGemstone
            gemstone = PhysicalGemstone.objects.create(
                species=species,
                variety=variety,
                lifecycle_state=data["lifecycle_state"],
                acquisition_date=data["acquisition_date"],
            )

            # 2. InventoryItem
            inv = InventoryItem.objects.create(
                physical_gemstone=gemstone,
                inventory_source=InventorySource.COMPANY_OWNED,
                custody_status=CustodyStatus.IN_HOUSE,
                current_location="Safe A — Drawer 1",
                is_certified=True,
                listing_status=data["listing_status"],
            )

            # 3. CertificationReport
            cert_data = data["cert"]
            cert, _ = CertificationReport.objects.get_or_create(
                laboratory=lab,
                report_number=cert_data["report_number"],
                defaults=dict(
                    physical_gemstone=gemstone,
                    report_type=cert_data["report_type"],
                    issue_date=cert_data["issue_date"],
                    natural_status=cert_data["natural_status"],
                    treatment_status=cert_data["treatment_status"],
                    origin_country=cert_data.get("origin_country", ""),
                    reported_carat_weight=cert_data.get("reported_carat_weight"),
                    reported_dimensions=cert_data.get("reported_dimensions", ""),
                    verification_status=cert_data["verification_status"],
                    is_primary=True,
                    is_active=True,
                ),
            )

            # 4. ProvenanceRecord
            prov_data = data["provenance"]
            prov_cert = cert if prov_data["confidence"] == ProvenanceConfidence.VERIFIED else None
            ProvenanceRecord.objects.create(
                physical_gemstone=gemstone,
                confidence=prov_data["confidence"],
                origin_country=prov_data.get("origin_country", ""),
                source_region=prov_data.get("source_region", ""),
                mine_locality=prov_data.get("mine_locality", ""),
                certification_report=prov_cert,
                customer_description=prov_data.get("customer_description", ""),
            )

            # 5. Product
            product = Product.objects.create(
                inventory_item=inv,
                price_usd=data["price_usd"],
                value_tier=data["value_tier"],
                headline=data["headline"],
                description=data["description"],
                listing_status=data["listing_status"],
            )

            # 6. ProductMedia
            for m in data["media"]:
                ProductMedia.objects.create(
                    product=product,
                    s3_key=m["s3_key"],
                    alt_text=m["alt_text"],
                    is_primary=m["is_primary"],
                    display_order=m["display_order"],
                )

            created += 1
            self.stdout.write(f"  Created: {product.headline} ({gemstone.gemstone_id})")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Created {created} products, skipped {skipped} already existing."
            )
        )
