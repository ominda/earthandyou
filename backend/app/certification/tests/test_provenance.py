from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from certification.models import (
    Laboratory,
    CertificationReport,
    ProvenanceRecord,
    ProvenanceConfidence,
    LaboratoryType,
    ReportType,
    NaturalStatus,
    TreatmentStatus,
)
from inventory.models import PhysicalGemstone
from catalog.models import GemstoneSpecies, GemstoneVariety


class ProvenanceTestSetup(TestCase):

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
            name="GemResearch Swisslab",
            code="GRS",
            laboratory_type=LaboratoryType.INTERNATIONAL,
        )
        self.report = CertificationReport.objects.create(
            physical_gemstone=self.gemstone,
            laboratory=self.lab,
            report_number="GRS-2026-001",
            report_type=ReportType.ORIGIN,
            issue_date=timezone.now().date(),
            natural_status=NaturalStatus.NATURAL,
            treatment_status=TreatmentStatus.UNHEATED,
            origin_country="Sri Lanka",
        )

    def make_provenance(self, **kwargs):
        defaults = {
            "physical_gemstone": self.gemstone,
            "confidence": ProvenanceConfidence.UNKNOWN,
        }
        defaults.update(kwargs)
        return ProvenanceRecord.objects.create(**defaults)


class ProvenanceRecordModelTest(ProvenanceTestSetup):

    def test_str_with_known_origin(self):
        prov = self.make_provenance(
            origin_country="Sri Lanka",
            confidence=ProvenanceConfidence.DOCUMENTED,
        )
        self.assertIn("Sri Lanka", str(prov))
        self.assertIn(self.gemstone.gemstone_id, str(prov))

    def test_str_with_unknown_origin(self):
        prov = self.make_provenance()
        self.assertIn("Unknown origin", str(prov))

    def test_defaults(self):
        prov = self.make_provenance()
        self.assertEqual(prov.confidence, ProvenanceConfidence.UNKNOWN)
        self.assertEqual(prov.origin_country, "")
        self.assertEqual(prov.source_region, "")
        self.assertEqual(prov.mine_locality, "")

    def test_one_to_one_with_gemstone(self):
        prov = self.make_provenance()
        self.assertEqual(self.gemstone.provenance, prov)

    def test_cannot_create_duplicate_provenance_for_same_gemstone(self):
        from django.db import IntegrityError
        self.make_provenance()
        with self.assertRaises(IntegrityError):
            ProvenanceRecord.objects.create(
                physical_gemstone=self.gemstone,
                confidence=ProvenanceConfidence.UNKNOWN,
            )

    def test_deleting_gemstone_is_protected(self):
        from django.db.models import ProtectedError
        self.make_provenance()
        with self.assertRaises(ProtectedError):
            self.gemstone.delete()

    def test_certification_report_optional(self):
        prov = self.make_provenance(confidence=ProvenanceConfidence.UNKNOWN)
        self.assertIsNone(prov.certification_report)

    def test_certification_report_nulled_when_report_deleted(self):
        prov = self.make_provenance(
            confidence=ProvenanceConfidence.DOCUMENTED,
            origin_country="Sri Lanka",
            certification_report=self.report,
        )
        # Deleting the report should set FK to null, not delete provenance
        self.report.delete()
        prov.refresh_from_db()
        self.assertIsNone(prov.certification_report)


class ProvenanceValidationTest(ProvenanceTestSetup):

    def test_verified_without_report_raises(self):
        prov = self.make_provenance(
            confidence=ProvenanceConfidence.VERIFIED,
            origin_country="Sri Lanka",
        )
        with self.assertRaises(ValidationError):
            prov.clean()

    def test_verified_without_origin_country_raises(self):
        prov = self.make_provenance(
            confidence=ProvenanceConfidence.VERIFIED,
            certification_report=self.report,
        )
        with self.assertRaises(ValidationError):
            prov.clean()

    def test_verified_with_report_and_country_passes(self):
        prov = self.make_provenance(
            confidence=ProvenanceConfidence.VERIFIED,
            origin_country="Sri Lanka",
            certification_report=self.report,
        )
        # Should not raise
        prov.clean()

    def test_documented_without_report_passes(self):
        prov = self.make_provenance(
            confidence=ProvenanceConfidence.DOCUMENTED,
            origin_country="Sri Lanka",
        )
        # DOCUMENTED does not require a lab report
        prov.clean()

    def test_seller_provided_passes_without_report(self):
        prov = self.make_provenance(
            confidence=ProvenanceConfidence.SELLER_PROVIDED,
            origin_country="Sri Lanka",
        )
        prov.clean()

    def test_unknown_passes_with_no_fields(self):
        prov = self.make_provenance(confidence=ProvenanceConfidence.UNKNOWN)
        prov.clean()


class ProvenanceSupportingDocumentsTest(ProvenanceTestSetup):

    def test_supporting_documents_returns_empty_list_when_blank(self):
        prov = self.make_provenance()
        self.assertEqual(prov.supporting_documents, [])

    def test_supporting_documents_returns_list_of_keys(self):
        prov = self.make_provenance(
            supporting_document_s3_keys=(
                "provenance/gem-001/receipt.pdf\n"
                "provenance/gem-001/export-cert.pdf\n"
            )
        )
        docs = prov.supporting_documents
        self.assertEqual(len(docs), 2)
        self.assertIn("provenance/gem-001/receipt.pdf", docs)
        self.assertIn("provenance/gem-001/export-cert.pdf", docs)

    def test_supporting_documents_strips_blank_lines(self):
        prov = self.make_provenance(
            supporting_document_s3_keys="provenance/gem-001/receipt.pdf\n\n"
        )
        self.assertEqual(len(prov.supporting_documents), 1)


class ProvenanceAuditFieldsTest(ProvenanceTestSetup):

    def test_created_at_is_set(self):
        prov = self.make_provenance()
        self.assertIsNotNone(prov.created_at)

    def test_updated_at_changes_on_save(self):
        prov = self.make_provenance()
        original = prov.updated_at
        prov.source_region = "Ratnapura District"
        prov.save()
        prov.refresh_from_db()
        self.assertGreaterEqual(prov.updated_at, original)
