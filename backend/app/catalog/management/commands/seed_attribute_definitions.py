from django.core.management.base import BaseCommand
from catalog.models import (
    GemstoneSpecies,
    GemstoneAttributeDefinition,
    GemstoneAttributeOption,
    AttributeDataType,
)

# Attributes shared across all species
COMMON_ATTRIBUTES = [
    {"name": "Shape", "key": "shape", "data_type": AttributeDataType.SELECT, "is_required": True, "is_filterable": True, "display_order": 1, "options": ["Round", "Oval", "Cushion", "Pear", "Emerald Cut", "Marquise", "Heart", "Trillion", "Square", "Cabochon", "Freeform"]},
    {"name": "Cut Style", "key": "cut_style", "data_type": AttributeDataType.SELECT, "is_required": False, "is_filterable": True, "display_order": 2, "options": ["Faceted", "Cabochon", "Mixed Cut", "Step Cut", "Brilliant Cut"]},
    {"name": "Carat Weight", "key": "carat_weight", "data_type": AttributeDataType.DECIMAL, "unit": "ct", "is_required": True, "is_filterable": True, "display_order": 3},
    {"name": "Length (mm)", "key": "length_mm", "data_type": AttributeDataType.DECIMAL, "unit": "mm", "is_required": False, "is_filterable": False, "display_order": 4},
    {"name": "Width (mm)", "key": "width_mm", "data_type": AttributeDataType.DECIMAL, "unit": "mm", "is_required": False, "is_filterable": False, "display_order": 5},
    {"name": "Depth (mm)", "key": "depth_mm", "data_type": AttributeDataType.DECIMAL, "unit": "mm", "is_required": False, "is_filterable": False, "display_order": 6},
    {"name": "Clarity", "key": "clarity", "data_type": AttributeDataType.SELECT, "is_required": False, "is_filterable": True, "display_order": 7, "options": ["Eye Clean", "Slightly Included", "Moderately Included", "Heavily Included"]},
]

# Species-specific attributes keyed by species code
SPECIES_ATTRIBUTES = {
    "COR": [
        {"name": "Primary Color", "key": "primary_color", "data_type": AttributeDataType.SELECT, "is_required": True, "is_filterable": True, "display_order": 10, "options": ["Blue", "Pink", "Yellow", "Orange", "White/Colourless", "Purple", "Green", "Red", "Multicolor"]},
        {"name": "Hue", "key": "hue", "data_type": AttributeDataType.TEXT, "is_required": False, "is_filterable": False, "display_order": 11},
        {"name": "Tone", "key": "tone", "data_type": AttributeDataType.SELECT, "is_required": False, "is_filterable": False, "display_order": 12, "options": ["Very Light", "Light", "Medium Light", "Medium", "Medium Dark", "Dark", "Very Dark"]},
        {"name": "Saturation", "key": "saturation", "data_type": AttributeDataType.SELECT, "is_required": False, "is_filterable": False, "display_order": 13, "options": ["Greyish", "Slightly Greyish", "Moderately Strong", "Strong", "Vivid"]},
        {"name": "Asterism", "key": "asterism", "data_type": AttributeDataType.BOOLEAN, "is_required": False, "is_filterable": True, "display_order": 14},
    ],
    "SPI": [
        {"name": "Primary Color", "key": "primary_color", "data_type": AttributeDataType.SELECT, "is_required": True, "is_filterable": True, "display_order": 10, "options": ["Red", "Pink", "Blue", "Violet", "Purple", "Orange", "Grey", "Black"]},
        {"name": "Tone", "key": "tone", "data_type": AttributeDataType.SELECT, "is_required": False, "is_filterable": False, "display_order": 11, "options": ["Very Light", "Light", "Medium Light", "Medium", "Medium Dark", "Dark", "Very Dark"]},
        {"name": "Saturation", "key": "saturation", "data_type": AttributeDataType.SELECT, "is_required": False, "is_filterable": False, "display_order": 12, "options": ["Greyish", "Slightly Greyish", "Moderately Strong", "Strong", "Vivid"]},
        {"name": "Colour Change", "key": "colour_change", "data_type": AttributeDataType.BOOLEAN, "is_required": False, "is_filterable": True, "display_order": 13},
    ],
    "CHR": [
        {"name": "Primary Color", "key": "primary_color", "data_type": AttributeDataType.SELECT, "is_required": True, "is_filterable": True, "display_order": 10, "options": ["Green", "Yellow-Green", "Yellow", "Honey", "Colour Change"]},
        {"name": "Colour Change Description", "key": "colour_change_description", "data_type": AttributeDataType.TEXT, "is_required": False, "is_filterable": False, "display_order": 11},
        {"name": "Chatoyancy", "key": "chatoyancy", "data_type": AttributeDataType.BOOLEAN, "is_required": False, "is_filterable": True, "display_order": 12},
        {"name": "Chatoyancy Strength", "key": "chatoyancy_strength", "data_type": AttributeDataType.SELECT, "is_required": False, "is_filterable": False, "display_order": 13, "options": ["Weak", "Moderate", "Strong", "Very Strong"]},
    ],
    "GAR": [
        {"name": "Primary Color", "key": "primary_color", "data_type": AttributeDataType.SELECT, "is_required": True, "is_filterable": True, "display_order": 10, "options": ["Red", "Orange", "Orange-Red", "Brown-Red", "Green", "Colour Change"]},
        {"name": "Colour Change", "key": "colour_change", "data_type": AttributeDataType.BOOLEAN, "is_required": False, "is_filterable": True, "display_order": 11},
        {"name": "Colour Change Description", "key": "colour_change_description", "data_type": AttributeDataType.TEXT, "is_required": False, "is_filterable": False, "display_order": 12},
    ],
    "ZIR": [
        {"name": "Primary Color", "key": "primary_color", "data_type": AttributeDataType.SELECT, "is_required": True, "is_filterable": True, "display_order": 10, "options": ["Blue", "Golden", "White/Colourless", "Red", "Green", "Brown"]},
        {"name": "Tone", "key": "tone", "data_type": AttributeDataType.SELECT, "is_required": False, "is_filterable": False, "display_order": 11, "options": ["Very Light", "Light", "Medium Light", "Medium", "Medium Dark", "Dark", "Very Dark"]},
    ],
    "TOU": [
        {"name": "Primary Color", "key": "primary_color", "data_type": AttributeDataType.SELECT, "is_required": True, "is_filterable": True, "display_order": 10, "options": ["Pink", "Red", "Green", "Blue", "Yellow", "Multicolor", "Watermelon"]},
        {"name": "Tone", "key": "tone", "data_type": AttributeDataType.SELECT, "is_required": False, "is_filterable": False, "display_order": 11, "options": ["Very Light", "Light", "Medium Light", "Medium", "Medium Dark", "Dark", "Very Dark"]},
        {"name": "Saturation", "key": "saturation", "data_type": AttributeDataType.SELECT, "is_required": False, "is_filterable": False, "display_order": 12, "options": ["Greyish", "Slightly Greyish", "Moderately Strong", "Strong", "Vivid"]},
    ],
}


class Command(BaseCommand):
    help = "Seed gemstone attribute definitions and options per species"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing attribute definitions before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            GemstoneAttributeDefinition.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared existing attribute definitions."))

        created_defs = 0
        created_opts = 0

        for species in GemstoneSpecies.objects.filter(is_active=True):
            all_attrs = COMMON_ATTRIBUTES + SPECIES_ATTRIBUTES.get(species.code, [])

            for attr in all_attrs:
                options_list = attr.pop("options", [])
                definition, created = GemstoneAttributeDefinition.objects.get_or_create(
                    species=species,
                    key=attr["key"],
                    defaults={k: v for k, v in attr.items() if k != "key"},
                )
                if created:
                    created_defs += 1

                for i, opt_value in enumerate(options_list):
                    _, opt_created = GemstoneAttributeOption.objects.get_or_create(
                        attribute=definition,
                        value=opt_value,
                        defaults={"display_order": i},
                    )
                    if opt_created:
                        created_opts += 1

                # Restore options list for idempotency
                attr["options"] = options_list

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_defs} attribute definitions and {created_opts} options."
            )
        )
