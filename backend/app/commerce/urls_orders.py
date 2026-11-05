from django.urls import path
from .views import OrderView, OrderDetailView, OrderPayView, OrderRefundView, OrderShipmentView, OrderExportView

urlpatterns = [
    path("", OrderView.as_view(), name="orders"),
    path("<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("<int:pk>/pay/", OrderPayView.as_view(), name="order-pay"),
    path("<int:pk>/refund/", OrderRefundView.as_view(), name="order-refund"),
    path("<int:pk>/shipment/", OrderShipmentView.as_view(), name="order-shipment"),
    path("<int:pk>/export/", OrderExportView.as_view(), name="order-export"),
]
