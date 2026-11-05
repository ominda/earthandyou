from django.urls import path
from .views import CheckoutView, CheckoutDetailView

urlpatterns = [
    path("", CheckoutView.as_view(), name="checkout"),
    path("<int:pk>/", CheckoutDetailView.as_view(), name="checkout-detail"),
]
