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
]
