from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from django.utils.html import format_html
from .models import Laboratory, CertificationReport, ProvenanceRecord, ProvenanceConfidence


class CertificationReportInline(admin.TabularInline):
    model = CertificationReport
    extra = 0
    fields = [
        "laboratory", "report_number", "report_type", "issue_date",
        "natural_status", "treatment_status", "is_primary",
        "verification_status", "is_active",
    ]
    readonly_fields = ["created_at", "updated_at"]


class ProvenanceRecordInline(admin.StackedInline):
    model = ProvenanceRecord
    extra = 0
    fields = [
        "confidence", "origin_country", "source_region", "mine_locality",
        "certification_report", "acquisition_source", "customer_description",
    ]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Laboratory)
class LaboratoryAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "laboratory_type", "is_active", "report_count"]
    list_filter = ["laboratory_type", "is_active"]
    search_fields = ["name", "code"]
    readonly_fields = ["created_at", "updated_at"]

    def report_count(self, obj):
        return obj.reports.count()
    report_count.short_description = "Reports"


def _set_as_primary(modeladmin, request, queryset):
    if queryset.count() != 1:
        modeladmin.message_user(
            request,
            "Select exactly one report to set as primary.",
            level=messages.WARNING,
        )
        return
    report = queryset.first()
    report.set_as_primary()
    modeladmin.message_user(
        request,
        f"{report} set as primary report for {report.physical_gemstone.gemstone_id}.",
    )

_set_as_primary.short_description = "Set selected report as primary"


def _set_as_verified(modeladmin, request, queryset):
    now = timezone.now()
    count = queryset.exclude(verification_status="verified").update(
        verification_status="verified",
        verified_at=now,
    )
    modeladmin.message_user(request, f"{count} report(s) marked as Verified.")

_set_as_verified.short_description = "Mark selected reports as Verified"


@admin.register(CertificationReport)
class CertificationReportAdmin(admin.ModelAdmin):
    list_display = [
        "report_number", "laboratory", "physical_gemstone",
        "report_type", "issue_date", "natural_status",
        "treatment_status", "is_primary", "verification_status", "is_active",
    ]
    list_filter = [
        "laboratory", "report_type", "natural_status",
        "treatment_status", "verification_status", "is_primary", "is_active",
    ]
    search_fields = [
        "report_number",
        "physical_gemstone__gemstone_id",
        "laboratory__code",
    ]
    readonly_fields = ["verification_url", "created_at", "updated_at"]
    actions = [_set_as_primary, _set_as_verified]
    fieldsets = [
        ("Gemstone & Laboratory", {
            "fields": ["physical_gemstone", "laboratory", "report_number", "report_type", "issue_date"],
        }),
        ("Gemstone Determination", {
            "fields": ["natural_status", "treatment_status", "treatment_details"],
        }),
        ("Origin", {
            "fields": ["origin_country", "origin_details"],
        }),
        ("Reported Measurements", {
            "fields": ["reported_carat_weight", "reported_dimensions"],
            "classes": ["collapse"],
        }),
        ("Document", {
            "fields": ["document_s3_key"],
            "classes": ["collapse"],
        }),
        ("Verification", {
            "fields": ["verification_status", "verification_url", "verified_at", "verification_notes"],
        }),
        ("Status", {
            "fields": ["is_primary", "is_active"],
        }),
        ("Audit", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    def verification_url(self, obj):
        url = obj.verification_url
        if url:
            return format_html('<a href="{}" target="_blank">{}</a>', url, url)
        return "—"
    verification_url.short_description = "Verification URL"


@admin.register(ProvenanceRecord)
class ProvenanceRecordAdmin(admin.ModelAdmin):
    list_display = [
        "physical_gemstone", "origin_country", "source_region",
        "mine_locality", "confidence", "has_certificate",
    ]
    list_filter = ["confidence", "origin_country"]
    search_fields = [
        "physical_gemstone__gemstone_id",
        "origin_country", "source_region", "mine_locality",
    ]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        ("Gemstone", {
            "fields": ["physical_gemstone"],
        }),
        ("Confidence", {
            "fields": ["confidence"],
        }),
        ("Geographic Origin", {
            "fields": ["origin_country", "source_region", "mine_locality"],
        }),
        ("Supporting Evidence", {
            "fields": ["certification_report", "supporting_document_s3_keys"],
        }),
        ("Acquisition", {
            "fields": ["acquisition_source", "acquisition_notes"],
            "classes": ["collapse"],
        }),
        ("Customer Facing", {
            "fields": ["customer_description"],
        }),
        ("Internal", {
            "fields": ["internal_notes"],
            "classes": ["collapse"],
        }),
        ("Audit", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    def has_certificate(self, obj):
        return obj.certification_report is not None
    has_certificate.boolean = True
    has_certificate.short_description = "Lab Confirmed"
