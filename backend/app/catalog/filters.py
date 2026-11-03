import django_filters
from django.db.models import Q
from .models import Product, ValueTier
from inventory.models import ListingStatus
from certification.models import TreatmentStatus, NaturalStatus


class ProductFilter(django_filters.FilterSet):
    # --- existing filters from 2.1 ---
    species = django_filters.CharFilter(
        field_name="inventory_item__physical_gemstone__species__code",
        lookup_expr="iexact",
    )
    variety = django_filters.CharFilter(
        field_name="inventory_item__physical_gemstone__variety__name",
        lookup_expr="iexact",
    )
    value_tier = django_filters.ChoiceFilter(choices=ValueTier.choices)
    price_min = django_filters.NumberFilter(field_name="price_usd", lookup_expr="gte")
    price_max = django_filters.NumberFilter(field_name="price_usd", lookup_expr="lte")
    available = django_filters.BooleanFilter(method="filter_available")

    # --- new filters for 2.3 ---
    treatment = django_filters.ChoiceFilter(
        choices=TreatmentStatus.choices,
        method="filter_treatment",
    )
    natural_status = django_filters.ChoiceFilter(
        choices=NaturalStatus.choices,
        method="filter_natural_status",
    )
    origin = django_filters.CharFilter(
        method="filter_origin",
    )
    is_certified = django_filters.BooleanFilter(
        field_name="inventory_item__is_certified",
    )
    carat_min = django_filters.NumberFilter(
        method="filter_carat_min",
    )
    carat_max = django_filters.NumberFilter(
        method="filter_carat_max",
    )
    search = django_filters.CharFilter(method="filter_search")
    ordering = django_filters.OrderingFilter(
        fields=(
            ("price_usd", "price"),
            ("created_at", "created_at"),
        ),
        field_labels={
            "price": "Price",
            "created_at": "Date Added",
        },
    )

    class Meta:
        model = Product
        fields = [
            "species", "variety", "value_tier", "price_min", "price_max",
            "available", "treatment", "natural_status", "origin",
            "is_certified", "carat_min", "carat_max", "search",
        ]

    def filter_available(self, queryset, name, value):
        if value:
            return queryset.filter(
                listing_status=ListingStatus.ACTIVE,
                inventory_item__is_reserved=False,
                inventory_item__is_sold=False,
            )
        return queryset

    def filter_treatment(self, queryset, name, value):
        return queryset.filter(
            inventory_item__physical_gemstone__certification_reports__treatment_status=value,
            inventory_item__physical_gemstone__certification_reports__is_active=True,
        ).distinct()

    def filter_natural_status(self, queryset, name, value):
        return queryset.filter(
            inventory_item__physical_gemstone__certification_reports__natural_status=value,
            inventory_item__physical_gemstone__certification_reports__is_active=True,
        ).distinct()

    def filter_origin(self, queryset, name, value):
        return queryset.filter(
            inventory_item__physical_gemstone__certification_reports__origin_country__icontains=value,
            inventory_item__physical_gemstone__certification_reports__is_active=True,
        ).distinct()

    def filter_carat_min(self, queryset, name, value):
        return queryset.filter(
            inventory_item__physical_gemstone__certification_reports__reported_carat_weight__gte=value,
            inventory_item__physical_gemstone__certification_reports__is_active=True,
        ).distinct()

    def filter_carat_max(self, queryset, name, value):
        return queryset.filter(
            inventory_item__physical_gemstone__certification_reports__reported_carat_weight__lte=value,
            inventory_item__physical_gemstone__certification_reports__is_active=True,
        ).distinct()

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(headline__icontains=value)
            | Q(inventory_item__physical_gemstone__gemstone_id__icontains=value)
            | Q(inventory_item__physical_gemstone__species__name__icontains=value)
            | Q(inventory_item__physical_gemstone__variety__name__icontains=value)
        ).distinct()
