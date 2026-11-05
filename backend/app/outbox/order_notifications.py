from .services import send_email


def notify_order_confirmed(order) -> None:
    send_email(
        recipient=order.customer.email,
        subject=f"Your order {order.order_ref} is confirmed",
        template_name="order_confirm",
        context={
            "order_ref": order.order_ref,
            "customer_name": order.customer.full_name or order.customer.email,
            "product_headline": order.product_headline,
            "gemstone_id": order.gemstone_id,
            "subtotal_usd": str(order.subtotal_usd),
            "shipping_usd": str(order.shipping_usd),
            "total_usd": str(order.total_usd),
            "shipping_address": order.shipping_address,
        },
    )


def notify_order_paid(order, payment) -> None:
    send_email(
        recipient=order.customer.email,
        subject=f"Payment received for {order.order_ref}",
        template_name="order_paid",
        context={
            "order_ref": order.order_ref,
            "customer_name": order.customer.full_name or order.customer.email,
            "amount_usd": str(payment.amount_usd),
            "provider": payment.provider,
            "provider_reference": payment.provider_reference,
        },
    )


def notify_order_dispatched(order, shipment) -> None:
    send_email(
        recipient=order.customer.email,
        subject=f"Your order {order.order_ref} has been dispatched",
        template_name="order_dispatched",
        context={
            "order_ref": order.order_ref,
            "customer_name": order.customer.full_name or order.customer.email,
            "carrier": shipment.carrier,
            "tracking_number": shipment.tracking_number,
            "tracking_url": shipment.tracking_url,
            "estimated_delivery_date": str(shipment.estimated_delivery_date) if shipment.estimated_delivery_date else "",
        },
    )


def notify_order_delivered(order, shipment) -> None:
    send_email(
        recipient=order.customer.email,
        subject=f"Your order {order.order_ref} has been delivered",
        template_name="order_delivered",
        context={
            "order_ref": order.order_ref,
            "customer_name": order.customer.full_name or order.customer.email,
            "gemstone_id": order.gemstone_id,
            "product_headline": order.product_headline,
        },
    )
