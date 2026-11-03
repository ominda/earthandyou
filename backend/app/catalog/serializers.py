from rest_framework import serializers
from .models import Product, ProductMedia
from certification.models import CertificationReport, ProvenanceRecord


class PrimaryMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMedia
        fields = ["s3_key", "alt_text"]


class ProductListSerializer(serializers.ModelSerializer):
    gemstone_id = serializers.CharField(source="inventory_item.physical_gemstone.gemstone_id")
    species = serializers.CharField(source="inventory_item.physical_gemstone.species.name")
    species_code = serializers.CharField(source="inventory_item.physical_gemstone.species.code")
    variety = serializers.SerializerMethodField()
    primary_media = serializers.SerializerMethodField()
    is_available = serializers.BooleanField()

    class Meta:
        model = Product
        fields = [
            "id",
            "gemstone_id",
            "slug",
            "species",
            "species_code",
            "variety",
            "headline",
            "price_usd",
            "value_tier",
            "listing_status",
            "is_available",
            "primary_media",
        ]

    def get_variety(self, obj):
        variety = obj.inventory_item.physical_gemstone.variety
        return variety.name if variety else None

    def get_primary_media(self, obj):
        primary = obj.media.filter(is_primary=True).first()
        if primary:
            return PrimaryMediaSerializer(primary).data
        return None


# ---------------------------------------------------------------------------
# Product detail serializers — module 2.2
# ---------------------------------------------------------------------------

class ProductMediaDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMedia
        fields = ["id", "media_type", "s3_key", "alt_text", "display_order", "is_primary"]


class CertificationReportSerializer(serializers.ModelSerializer):
    laboratory_name = serializers.CharField(source="laboratory.name")
    laboratory_code = serializers.CharField(source="laboratory.code")
    verification_url = serializers.CharField()

    class Meta:
        model = CertificationReport
        fields = [
            "id",
            "laboratory_name",
            "laboratory_code",
            "report_number",
            "report_type",
            "issue_date",
            "natural_status",
            "treatment_status",
            "treatment_details",
            "origin_country",
            "reported_carat_weight",
            "reported_dimensions",
            "verification_status",
            "verification_url",
            "is_primary",
        ]


class ProvenanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProvenanceRecord
        fields = [
            "confidence",
            "origin_country",
            "source_region",
            "mine_locality",
            "customer_description",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    gemstone_id = serializers.CharField(source="inventory_item.physical_gemstone.gemstone_id")
    species = serializers.CharField(source="inventory_item.physical_gemstone.species.name")
    species_code = serializers.CharField(source="inventory_item.physical_gemstone.species.code")
    variety = serializers.SerializerMethodField()
    is_available = serializers.BooleanField()
    media = ProductMediaDetailSerializer(many=True)
    certification_reports = serializers.SerializerMethodField()
    provenance = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "gemstone_id",
            "slug",
            "species",
            "species_code",
            "variety",
            "headline",
            "description",
            "price_usd",
            "value_tier",
            "listing_status",
            "is_available",
            "meta_title",
            "meta_description",
            "media",
            "certification_reports",
            "provenance",
        ]

    def get_variety(self, obj):
        variety = obj.inventory_item.physical_gemstone.variety
        return variety.name if variety else None

    def get_certification_reports(self, obj):
        reports = obj.inventory_item.physical_gemstone.certification_reports.filter(
            is_active=True
        ).select_related("laboratory").order_by("-is_primary", "-issue_date")
        return CertificationReportSerializer(reports, many=True).data

    def get_provenance(self, obj):
        try:
            provenance = obj.inventory_item.physical_gemstone.provenance
            return ProvenanceSerializer(provenance).data
        except ProvenanceRecord.DoesNotExist:
            return None
