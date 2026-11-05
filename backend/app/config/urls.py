from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({"status": "ok", "service": "earthandyou-api"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check),
    path("api/v1/catalog/", include("catalog.urls")),
    path("api/v1/auth/", include("customers.urls")),
    path("api/v1/staff/", include("customers.urls_staff")),
    path("api/v1/cart/", include("commerce.urls")),
    path("api/v1/reservations/", include("commerce.urls_reservations")),
    path("api/v1/checkout/", include("commerce.urls_checkout")),
    path("api/v1/orders/", include("commerce.urls_orders")),
    path("api/v1/webhooks/", include("commerce.urls_webhooks")),
    path("api/v1/shipping-rates/", include("commerce.urls_shipping")),
    path("api/v1/tracking/", include("commerce.urls_tracking")),
]
