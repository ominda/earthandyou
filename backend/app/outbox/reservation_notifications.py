from .services import send_email


def notify_reservation_created(reservation) -> None:
    send_email(
        recipient=reservation.customer.email,
        subject=f"Your reservation for {reservation.product.gemstone_id} is active",
        template_name="reservation_created",
        context={
            "customer_name": reservation.customer.full_name or reservation.customer.email,
            "gemstone_id": reservation.product.gemstone_id,
            "product_headline": reservation.product.headline,
            "expires_at": reservation.expires_at.strftime("%Y-%m-%d %H:%M UTC"),
        },
    )


def notify_reservation_expired(reservation) -> None:
    send_email(
        recipient=reservation.customer.email,
        subject=f"Your reservation for {reservation.product.gemstone_id} has expired",
        template_name="reservation_expired",
        context={
            "customer_name": reservation.customer.full_name or reservation.customer.email,
            "gemstone_id": reservation.product.gemstone_id,
            "product_headline": reservation.product.headline,
        },
    )
