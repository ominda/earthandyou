from django.core.management.base import BaseCommand
from certification.models import Laboratory, LaboratoryType


LABORATORIES = [
    {
        "name": "National Gem and Jewellery Authority",
        "code": "NGJA",
        "laboratory_type": LaboratoryType.LOCAL,
        "website": "https://www.ngja.gov.lk",
        "verification_url_template": "",
    },
    {
        "name": "Gemological Institute of America",
        "code": "GIA",
        "laboratory_type": LaboratoryType.INTERNATIONAL,
        "website": "https://www.gia.edu",
        "verification_url_template": "https://www.gia.edu/report-check?reportno={report_number}",
    },
    {
        "name": "GemResearch Swisslab",
        "code": "GRS",
        "laboratory_type": LaboratoryType.INTERNATIONAL,
        "website": "https://www.gemresearch.ch",
        "verification_url_template": "https://www.gemresearch.ch/report-check/?report_nr={report_number}",
    },
    {
        "name": "Swiss Gemmological Institute",
        "code": "SSEF",
        "laboratory_type": LaboratoryType.INTERNATIONAL,
        "website": "https://www.ssef.ch",
        "verification_url_template": "",
    },
    {
        "name": "Gübelin Gem Lab",
        "code": "GGL",
        "laboratory_type": LaboratoryType.INTERNATIONAL,
        "website": "https://www.gubelingemlab.com",
        "verification_url_template": "",
    },
]


class Command(BaseCommand):
    help = "Seed the database with gemological laboratories"

    def handle(self, *args, **options):
        created_count = 0
        for lab_data in LABORATORIES:
            _, created = Laboratory.objects.get_or_create(
                code=lab_data["code"],
                defaults=lab_data,
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created_count} laboratories.")
        )
