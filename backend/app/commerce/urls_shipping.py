from django.urls import path
from .views import ShippingRateView

urlpatterns = [
    path("", ShippingRateView.as_view(), name="shipping-rates"),
    path("<str:tier>/", ShippingRateView.as_view(), name="shipping-rate-detail"),
]
