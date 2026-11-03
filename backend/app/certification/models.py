from django.db import models
from django.core.exceptions import ValidationError
from inventory.models import PhysicalGemstone


class LaboratoryType(models.TextChoices):
    LOCAL = "local", "Local"
    INTERNATIONAL = "international", "International"


class ReportType(models.TextChoices):
    IDENTIFICATION = "identification", "Identification Report"
    GEMOLOGICAL = "gemological", "Gemological Report"
    ORIGIN = "origin", "Origin Report"
    ORIGIN_TREATMENT = "origin_treatment", "Origin & Treatment Report"
    TREATMENT = "treatment", "Treatment Report"


class NaturalStatus(models.TextChoices):
    NATURAL = "natural", "Natural"
    SYNTHETIC = "synthetic", "Synthetic"
    SIMULANT = "simulant", "Simulant"
    UNDETERMINED = "undetermined", "Undetermined"


class TreatmentStatus(models.TextChoices):
    # These are explicit states — never infer from natural status
    UNHEATED = "unheated", "Unheated"
    HEATED = "heated", "Heated (Heat Treatment)"
    TREATED = "treated", "Treated (Other Treatment)"
    NO_INDICATIONS = "no_indications", "No Indications of Treatment"
    NOT_ESTABLISHED = "not_established", "Not Established"
    UNKNOWN = "unknown", "Unknown"


class VerificationStatus(models.TextChoices):
    UNVERIFIED = "unverified", "Unverified"
    VERIFIED = "verified", "Verified"
    FAILED = "failed", "Verification Failed"
    EXPIRED = "expired", "Expired"


class Laboratory(models.Model):
    """
    A gemological laboratory that issues certification reports.

    Examples:
    - NGJA  (National Gem and Jewellery Authority — Sri Lanka, local)
    - GIA   (Gemological Institute of America — international)
    - GRS   (GemResearch Swisslab — international)
    - SSEF  (Swiss Gemmological Institute — international)
    - Gübelin (Gübelin Gem Lab — international)
    """

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    laboratory_type = models.CharField(
        max_length=20,
        choices=LaboratoryType.choices,
        default=LaboratoryType.LOCAL,
    )
    website = models.URLField(blank=True)
    verification_url_template = models.CharField(
        max_length=300,
        blank=True,
        help_text=(
            "URL template for online report verification. "
            "Use {report_number} as placeholder. "
            "e.g. https://www.gia.edu/report-check?reportno={report_number}"
        ),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Laboratory"
        verbose_name_plural = "Laboratories"
        ordering = ["laboratory_type", "name"]

    def __str__(self):
        return f"{self.code} — {self.name}"

    def get_verification_url(self, report_number: str) -> str:
        if self.verification_url_template and report_number:
            return self.verification_url_template.replace("{report_number}", report_number)
        return ""


class CertificationReport(models.Model):
    """
    A gemological report issued by a laboratory for a specific physical gemstone.

    Key design rules:
    - A gemstone may have more than one report (e.g. local NGJA + international GIA).
    - Only one report can be marked as primary at a time.
    - Treatment status is always explicit — never inferred from natural status.
    - Natural does NOT mean untreated. These are separate fields.
    - Report documents (PDF/image) are stored in S3 — this model stores the reference key.
    - Verification URL is derived from the laboratory template + report number.
    """

    physical_gemstone = models.ForeignKey(
        PhysicalGemstone,
        on_delete=models.PROTECT,
        related_name="certification_reports",
    )
    laboratory = models.ForeignKey(
        Laboratory,
        on_delete=models.PROTECT,
        related_name="reports",
    )

    report_number = models.CharField(max_length=100)
    report_type = models.CharField(
        max_length=30,
        choices=ReportType.choices,
        default=ReportType.IDENTIFICATION,
    )
    issue_date = models.DateField()

    # Natural/synthetic determination
    natural_status = models.CharField(
        max_length=20,
        choices=NaturalStatus.choices,
        default=NaturalStatus.NATURAL,
    )

    # Treatment — always explicit, never inferred
    treatment_status = models.CharField(
        max_length=30,
        choices=TreatmentStatus.choices,
        default=TreatmentStatus.UNKNOWN,
    )
    treatment_details = models.TextField(
        blank=True,
        help_text="Additional treatment details as stated in the report",
    )

    # Origin — only populated when the report includes origin determination
    origin_country = models.CharField(
        max_length=100,
        blank=True,
        help_text="Country of origin as stated in the report, e.g. 'Sri Lanka'",
    )
    origin_details = models.TextField(
        blank=True,
        help_text="Additional origin information as stated in the report",
    )

    # Weight & dimensions as stated in the report
    # These may differ slightly from internal measurements
    reported_carat_weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    reported_dimensions = models.CharField(
        max_length=100,
        blank=True,
        help_text="Dimensions as stated in the report, e.g. '8.23 x 6.11 x 4.02 mm'",
    )

    # Document storage — S3 key, not a full URL (signed URLs generated on demand)
    document_s3_key = models.CharField(
        max_length=500,
        blank=True,
        help_text="S3 object key for the report document (PDF or image)",
    )

    # Verification
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)

    # Primary report flag — only one report per gemstone should be primary
    is_primary = models.BooleanField(
        default=False,
        help_text="The primary report shown on the product page",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Inactive reports are superseded or withdrawn",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Certification Report"
        verbose_name_plural = "Certification Reports"
        ordering = ["-issue_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["laboratory", "report_number"],
                name="unique_report_number_per_laboratory",
            )
        ]

    def __str__(self):
        return (
            f"{self.laboratory.code} {self.report_number} — "
            f"{self.physical_gemstone.gemstone_id}"
        )

    def clean(self):
        # Validate that variety belongs to the gemstone's species
        if self.treatment_status == TreatmentStatus.UNHEATED and self.natural_status != NaturalStatus.NATURAL:
            raise ValidationError(
                "Treatment status 'Unheated' is only applicable to natural gemstones."
            )

    @property
    def verification_url(self) -> str:
        return self.laboratory.get_verification_url(self.report_number)

    def set_as_primary(self) -> None:
        """
        Sets this report as the primary report for its gemstone.
        Demotes any other primary report for the same gemstone.
        """
        CertificationReport.objects.filter(
            physical_gemstone=self.physical_gemstone,
            is_primary=True,
        ).exclude(pk=self.pk).update(is_primary=False)
        self.is_primary = True
        self.save(update_fields=["is_primary", "updated_at"])


# ---------------------------------------------------------------------------
# Provenance — module 1.7
# ---------------------------------------------------------------------------

class ProvenanceConfidence(models.TextChoices):
    """
    How confident we are in the provenance information.

    Rules:
    - VERIFIED   — confirmed by a laboratory origin report or official documentation
    - DOCUMENTED — supported by written records (purchase receipts, export docs)
    - SELLER_PROVIDED — stated by the seller, not independently confirmed
    - UNKNOWN    — no provenance information available

    Never invent provenance. If unknown, use UNKNOWN.
    """
    VERIFIED = "verified", "Verified"
    DOCUMENTED = "documented", "Documented"
    SELLER_PROVIDED = "seller_provided", "Seller Provided"
    UNKNOWN = "unknown", "Unknown"


class ProvenanceRecord(models.Model):
    """
    Records the known origin and acquisition history of a physical gemstone.

    Design rules:
    - Provenance is never invented. If information is unavailable, confidence = UNKNOWN.
    - A gemstone may have one ProvenanceRecord. It is updated as more information
      becomes available rather than creating multiple records.
    - The certification_report field links to a lab report that confirms origin
      (e.g. a GRS or SSEF origin report). This is optional — not all gemstones
      will have a laboratory-confirmed origin.
    - Supporting documents (receipts, export papers) are stored in S3.
    - Customer-facing fields: source_region, mine_locality, origin_country,
      confidence, and customer_description.
    - Internal fields: acquisition_source, acquisition_notes, internal_notes.
    """

    physical_gemstone = models.OneToOneField(
        PhysicalGemstone,
        on_delete=models.PROTECT,
        related_name="provenance",
    )

    # Confidence level — always explicit
    confidence = models.CharField(
        max_length=20,
        choices=ProvenanceConfidence.choices,
        default=ProvenanceConfidence.UNKNOWN,
    )

    # Geographic origin
    origin_country = models.CharField(
        max_length=100,
        blank=True,
        help_text="Country of origin, e.g. 'Sri Lanka'",
    )
    source_region = models.CharField(
        max_length=200,
        blank=True,
        help_text="Region or district, e.g. 'Ratnapura District'",
    )
    mine_locality = models.CharField(
        max_length=200,
        blank=True,
        help_text="Specific mine or locality if known, e.g. 'Elahera'",
    )

    # Link to a laboratory origin report if one exists
    certification_report = models.ForeignKey(
        CertificationReport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="provenance_records",
        help_text="Laboratory origin report that confirms this provenance",
    )

    # Acquisition history
    acquisition_source = models.CharField(
        max_length=200,
        blank=True,
        help_text="Internal: who or where the gemstone was acquired from",
    )
    acquisition_notes = models.TextField(
        blank=True,
        help_text="Internal: acquisition context and history",
    )

    # Supporting documentation stored in S3
    # Comma-separated S3 keys for multiple documents
    supporting_document_s3_keys = models.TextField(
        blank=True,
        help_text="S3 object keys for supporting documents, one per line",
    )

    # Customer-facing description — written by content/product team
    customer_description = models.TextField(
        blank=True,
        help_text=(
            "Customer-facing provenance description. "
            "Must accurately reflect the confidence level. "
            "Do not overstate certainty."
        ),
    )

    internal_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Provenance Record"
        verbose_name_plural = "Provenance Records"
        ordering = ["-created_at"]

    def __str__(self):
        origin = self.origin_country or "Unknown origin"
        return (
            f"{self.physical_gemstone.gemstone_id} — "
            f"{origin} ({self.get_confidence_display()})"
        )

    def clean(self):
        # VERIFIED confidence requires a linked certification report
        if (
            self.confidence == ProvenanceConfidence.VERIFIED
            and not self.certification_report_id
        ):
            raise ValidationError(
                "Provenance confidence 'Verified' requires a linked certification report."
            )

        # VERIFIED confidence requires an origin country
        if (
            self.confidence == ProvenanceConfidence.VERIFIED
            and not self.origin_country
        ):
            raise ValidationError(
                "Provenance confidence 'Verified' requires an origin country."
            )

    @property
    def supporting_documents(self) -> list:
        """Returns supporting document S3 keys as a list."""
        if not self.supporting_document_s3_keys:
            return []
        return [
            key.strip()
            for key in self.supporting_document_s3_keys.splitlines()
            if key.strip()
        ]
