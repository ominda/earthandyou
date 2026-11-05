from django.urls import path
from .views import ReservationView, ReservationDetailView

urlpatterns = [
    path("", ReservationView.as_view(), name="reservations"),
    path("<int:pk>/", ReservationDetailView.as_view(), name="reservation-detail"),
]
