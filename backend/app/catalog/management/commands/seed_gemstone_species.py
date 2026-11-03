from django.core.management.base import BaseCommand
from catalog.models import GemstoneSpecies, GemstoneVariety


SEED_DATA = [
    {
        "name": "Corundum",
        "common_name": "Sapphire & Ruby",
        "code": "COR",
        "description": "Aluminium oxide mineral. Sri Lanka is one of the world's most important sources of fine corundum.",
        "varieties": [
            {"name": "Blue Sapphire", "code": "BSAP", "typical_colors": "Pale blue to deep royal blue, cornflower blue"},
            {"name": "Padparadscha Sapphire", "code": "PAD", "typical_colors": "Pinkish-orange to orangy-pink"},
            {"name": "Pink Sapphire", "code": "PSAP", "typical_colors": "Light pink to vivid pink"},
            {"name": "Yellow Sapphire", "code": "YSAP", "typical_colors": "Light yellow to golden yellow"},
            {"name": "White Sapphire", "code": "WSAP", "typical_colors": "Colourless"},
            {"name": "Star Sapphire", "code": "STSAP", "typical_colors": "Blue, grey, black with asterism"},
            {"name": "Colour Change Sapphire", "code": "CCSAP", "typical_colors": "Blue in daylight, violet/purple in incandescent light"},
            {"name": "Ruby", "code": "RUB", "typical_colors": "Pinkish-red to deep red"},
            {"name": "Star Ruby", "code": "STRUB", "typical_colors": "Red with asterism"},
        ],
    },
    {
        "name": "Spinel",
        "common_name": "Spinel",
        "code": "SPI",
        "description": "Magnesium aluminium oxide. Ceylon spinel is highly regarded, historically confused with ruby and sapphire.",
        "varieties": [
            {"name": "Red Spinel", "code": "RSPI", "typical_colors": "Orange-red to deep red"},
            {"name": "Pink Spinel", "code": "PSPI", "typical_colors": "Light pink to hot pink"},
            {"name": "Blue Spinel", "code": "BSPI", "typical_colors": "Pale blue to cobalt blue"},
            {"name": "Violet Spinel", "code": "VSPI", "typical_colors": "Violet to purple"},
            {"name": "Colour Change Spinel", "code": "CCSPI", "typical_colors": "Greyish-blue to purple"},
        ],
    },
    {
        "name": "Chrysoberyl",
        "common_name": "Alexandrite & Cat's Eye",
        "code": "CHR",
        "description": "Beryllium aluminium oxide. Sri Lanka produces fine alexandrite and cat's eye chrysoberyl.",
        "varieties": [
            {"name": "Alexandrite", "code": "ALE", "typical_colors": "Green in daylight, red/purplish-red in incandescent light"},
            {"name": "Cat's Eye Chrysoberyl", "code": "CAT", "typical_colors": "Honey yellow to greenish with chatoyancy"},
            {"name": "Yellow Chrysoberyl", "code": "YCHR", "typical_colors": "Yellow to greenish-yellow"},
        ],
    },
    {
        "name": "Garnet",
        "common_name": "Garnet",
        "code": "GAR",
        "description": "Silicate mineral group. Sri Lanka produces several garnet varieties including hessonite and almandine.",
        "varieties": [
            {"name": "Hessonite Garnet", "code": "HES", "typical_colors": "Orange to reddish-orange, cinnamon"},
            {"name": "Almandine Garnet", "code": "ALM", "typical_colors": "Deep red to reddish-brown"},
            {"name": "Pyrope Garnet", "code": "PYR", "typical_colors": "Deep red"},
            {"name": "Colour Change Garnet", "code": "CCGAR", "typical_colors": "Bluish-green in daylight, purplish-red in incandescent light"},
        ],
    },
    {
        "name": "Zircon",
        "common_name": "Zircon",
        "code": "ZIR",
        "description": "Zirconium silicate. Sri Lanka is a major source of fine zircon in multiple colours.",
        "varieties": [
            {"name": "Blue Zircon", "code": "BZIR", "typical_colors": "Sky blue to deep blue"},
            {"name": "Golden Zircon", "code": "GZIR", "typical_colors": "Yellow to golden orange"},
            {"name": "White Zircon", "code": "WZIR", "typical_colors": "Colourless, high brilliance"},
            {"name": "Red Zircon", "code": "RZIR", "typical_colors": "Red to reddish-brown"},
        ],
    },
    {
        "name": "Tourmaline",
        "common_name": "Tourmaline",
        "code": "TOU",
        "description": "Boron silicate mineral group. Sri Lanka produces a range of tourmaline colours.",
        "varieties": [
            {"name": "Pink Tourmaline", "code": "PTOU", "typical_colors": "Light pink to deep pink"},
            {"name": "Green Tourmaline", "code": "GTOU", "typical_colors": "Light green to deep green"},
            {"name": "Blue Tourmaline", "code": "BTOU", "typical_colors": "Blue to blue-green"},
            {"name": "Watermelon Tourmaline", "code": "WTOU", "typical_colors": "Pink centre with green rim"},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the database with Sri Lankan gemstone species and varieties"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing species and varieties before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            GemstoneVariety.objects.all().delete()
            GemstoneSpecies.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared existing data."))

        created_species = 0
        created_varieties = 0

        for item in SEED_DATA:
            varieties = item["varieties"]
            species, created = GemstoneSpecies.objects.get_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "common_name": item["common_name"],
                    "description": item["description"],
                },
            )
            if created:
                created_species += 1

            for v in varieties:
                _, created = GemstoneVariety.objects.get_or_create(
                    species=species,
                    code=v["code"],
                    defaults={"name": v["name"], "typical_colors": v["typical_colors"]},
                )
                if created:
                    created_varieties += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_species} species and {created_varieties} varieties."
            )
        )
