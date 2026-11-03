from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from certification.models import (
    Laboratory,
    CertificationReport,
    LaboratoryType,
    ReportType,
    NaturalStatus,
    TreatmentStatus,
    VerificationStatus,
)
from inventory.models import PhysicalGemstone
from catalog.models import GemstoneSpecies, GemstoneVariety


class CertificationTestSetup(TestCase):

    def setUp(self):
        self.species = GemstoneSpecies.objects.create(
            name="Corundum", common_name="Sapphire & Ruby", code="COR"
        )
        self.variety = GemstoneVariety.objects.create(
            species=self.species, name="Blue Sapphire", code="BSAP"
        )
        self.gemstone = PhysicalGemstone.objects.create(
            species=self.species,
            variety=self.variety,
            acquisition_date=timezone.now().date(),
        )
        self.lab = Laboratory.objects.create(
            name="National Gem and Jewellery Authority",
            code="NGJA",
            laboratory_type=LaboratoryType.LOCAL,
        )

    def make_report(self, **kwargs):
        defaults = {
            "physical_gemstone": self.gemstone,
            "laboratory": self.lab,
            "report_number": "NGJA-2026-001",
            "report_type": ReportType.IDENTIFICATION,
            "issue_date": timezone.now().date(),
            "natural_status": NaturalStatus.NATURAL,
            "treatment_status": TreatmentStatus.UNHEATED,
        }
        defaults.update(kwargs)
        return CertificationReport.objects.create(**defaults)


class LaboratoryModelTest(CertificationTestSetup):

    def test_str(self):
        self.assertEqual(str(self.lab), "NGJA — National Gem and Jewellery Authority")

    def test_code_is_unique(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Laboratory.objects.create(
                name="Duplicate Lab",
                code="NGJA",
            )

    def test_name_is_unique(self):
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Laboratory.objects.create(
                name="National Gem and Jewellery Authority",
                code="NGJA2",
            )

    def test_is_active_defaults_true(self):
        self.assertTrue(self.lab.is_active)

    def test_default_laboratory_type(self):
        self.assertEqual(self.lab.laboratory_type, LaboratoryType.LOCAL)

    def test_get_verification_url_with_template(self):
        gia = Laboratory.objects.create(
            name="Gemological Institute of America",
            code="GIA",
            laboratory_type=LaboratoryType.INTERNATIONAL,
            verification_url_template="https://www.gia.edu/report-check?reportno={report_number}",
        )
        url = gia.get_verification_url("1234567890")
        self.assertEqual(url, "https://www.gia.edu/report-check?reportno=1234567890")

    def test_get_verification_url_without_template_returns_empty(self):
        url = self.lab.get_verification_url("NGJA-001")
        self.assertEqual(url, "")

    def test_get_verification_url_with_empty_report_number_returns_empty(self):
        gia = Laboratory.objects.create(
            name="GIA",
            code="GIA2",
            verification_url_template="https://www.gia.edu/report-check?reportno={report_number}",
        )
        self.assertEqual(gia.get_verification_url(""), "")


class CertificationReportModelTest(CertificationTestSetup):

    def test_str(self):
        report = self.make_report()
        self.assertIn("NGJA", str(report))
        self.assertIn(self.gemstone.gemstone_id, str(report))

    def test_defaults(self):
        report = self.make_report()
        self.assertFalse(report.is_primary)
        self.assertTrue(report.is_active)
        self.assertEqual(report.verification_status, VerificationStatus.UNVERIFIED)

    def test_unique_report_number_per_laboratory(self):
        from django.db import IntegrityError
        self.make_report()
        with self.assertRaises(IntegrityError):
            self.make_report(report_number="NGJA-2026-001")

    def test_same_report_number_allowed_for_different_labs(self):
        gia = Laboratory.objects.create(
            name="GIA", code="GIA",
            laboratory_type=LaboratoryType.INTERNATIONAL,
        )
        self.make_report(report_number="REP-001")
        report2 = self.make_report(laboratory=gia, report_number="REP-001")
        self.assertEqual(report2.laboratory, gia)

    def test_gemstone_can_have_multiple_reports(self):
        gia = Laboratory.objects.create(
            name="GIA", code="GIA",
            laboratory_type=LaboratoryType.INTERNATIONAL,
        )
        self.make_report(report_number="NGJA-001")
        self.make_report(laboratory=gia, report_number="GIA-001")
        self.assertEqual(
            self.gemstone.certification_reports.count(), 2
        )

    def test_verification_url_property(self):
        gia = Laboratory.objects.create(
            name="GIA", code="GIA",
            laboratory_type=LaboratoryType.INTERNATIONAL,
            verification_url_template="https://www.gia.edu/report-check?reportno={report_number}",
        )
        report = self.make_report(laboratory=gia, report_number="9876543210")
        self.assertIn("9876543210", report.verification_url)

    def test_unheated_treatment_on_non_natural_raises_validation_error(self):
        report = self.make_report(
            natural_status=NaturalStatus.SYNTHETIC,
            treatment_status=TreatmentStatus.UNHEATED,
        )
        with self.assertRaises(ValidationError):
            report.clean()

    def test_unheated_on_natural_passes_validation(self):
        report = self.make_report(
            natural_status=NaturalStatus.NATURAL,
            treatment_status=TreatmentStatus.UNHEATED,
        )
        # Should not raise
        report.clean()

    def test_deleting_gemstone_is_protected(self):
        from django.db.models import ProtectedError
        self.make_report()
        with self.assertRaises(ProtectedError):
            self.gemstone.delete()


class SetAsPrimaryTest(CertificationTestSetup):

    def test_set_as_primary_marks_report_primary(self):
        report = self.make_report()
        report.set_as_primary()
        report.refresh_from_db()
        self.assertTrue(report.is_primary)

    def test_set_as_primary_demotes_previous_primary(self):
        gia = Laboratory.objects.create(
            name="GIA", code="GIA",
            laboratory_type=LaboratoryType.INTERNATIONAL,
        )
        report1 = self.make_report(report_number="NGJA-001")
        report1.set_as_primary()

        report2 = self.make_report(laboratory=gia, report_number="GIA-001")
        report2.set_as_primary()

        report1.refresh_from_db()
        report2.refresh_from_db()
        self.assertFalse(report1.is_primary)
        self.assertTrue(report2.is_primary)

    def test_only_one_primary_report_per_gemstone(self):
        gia = Laboratory.objects.create(
            name="GIA", code="GIA",
            laboratory_type=LaboratoryType.INTERNATIONAL,
        )
        report1 = self.make_report(report_number="NGJA-001")
        report2 = self.make_report(laboratory=gia, report_number="GIA-001")
        report1.set_as_primary()
        report2.set_as_primary()

        primary_count = CertificationReport.objects.filter(
            physical_gemstone=self.gemstone,
            is_primary=True,
        ).count()
        self.assertEqual(primary_count, 1)


class SeedLaboratoriesCommandTest(TestCase):

    def test_seed_creates_laboratories(self):
        from django.core.management import call_command
        call_command("seed_laboratories", verbosity=0)
        self.assertGreater(Laboratory.objects.count(), 0)

    def test_seed_includes_ngja(self):
        from django.core.management import call_command
        call_command("seed_laboratories", verbosity=0)
        self.assertTrue(Laboratory.objects.filter(code="NGJA").exists())

    def test_seed_is_idempotent(self):
        from django.core.management import call_command
        call_command("seed_laboratories", verbosity=0)
        count = Laboratory.objects.count()
        call_command("seed_laboratories", verbosity=0)
        self.assertEqual(Laboratory.objects.count(), count)
