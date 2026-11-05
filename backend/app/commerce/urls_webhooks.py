from django.urls import path
from .views import WebXPayWebhookView

urlpatterns = [
    path("webxpay/", WebXPayWebhookView.as_view(), name="webhook-webxpay"),
]
