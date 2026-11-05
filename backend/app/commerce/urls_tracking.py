from django.urls import path
from .views import OrderTrackingView

urlpatterns = [
    path("<str:order_ref>/", OrderTrackingView.as_view(), name="order-tracking"),
]
