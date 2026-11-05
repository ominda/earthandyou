from django.urls import path
from .views import CartView, CartItemView, ReservationView, ReservationDetailView

urlpatterns = [
    path("", CartView.as_view(), name="cart"),
    path("items/", CartItemView.as_view(), name="cart-items"),
    path("items/<int:product_id>/", CartItemView.as_view(), name="cart-item-detail"),
]
