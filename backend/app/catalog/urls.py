from django.urls import path
from .views import ProductListView, ProductDetailView, MediaSignedUrlView

urlpatterns = [
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
    path("media/sign/", MediaSignedUrlView.as_view(), name="media-sign"),
]
