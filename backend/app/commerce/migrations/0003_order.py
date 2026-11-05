# Generated migration for module 4.3 + 4.4 — CheckoutSession, Order, OrderStatusLog

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("commerce", "0002_reservation_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CheckoutSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("shipping_address", models.JSONField()),
                ("billing_address", models.JSONField()),
                ("subtotal_usd", models.DecimalField(decimal_places=2, max_digits=12)),
                ("shipping_usd", models.DecimalField(decimal_places=2, max_digits=12)),
                ("total_usd", models.DecimalField(decimal_places=2, max_digits=12)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("completed", "Completed"),
                            ("abandoned", "Abandoned"),
                            ("expired", "Expired"),
                        ],
                        default="pending",
                        max_length=10,
                    ),
                ),
                ("expires_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="checkout_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reservation",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="checkout_session",
                        to="commerce.reservation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Checkout Session",
                "verbose_name_plural": "Checkout Sessions",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_ref", models.CharField(editable=False, max_length=30, unique=True)),
                ("gemstone_id", models.CharField(max_length=30)),
                ("product_headline", models.CharField(blank=True, max_length=200)),
                ("product_slug", models.SlugField(max_length=60)),
                ("subtotal_usd", models.DecimalField(decimal_places=2, max_digits=12)),
                ("shipping_usd", models.DecimalField(decimal_places=2, max_digits=12)),
                ("total_usd", models.DecimalField(decimal_places=2, max_digits=12)),
                ("shipping_address", models.JSONField()),
                ("billing_address", models.JSONField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending_payment", "Pending Payment"),
                            ("confirmed", "Confirmed"),
                            ("processing", "Processing"),
                            ("shipped", "Shipped"),
                            ("delivered", "Delivered"),
                            ("cancelled", "Cancelled"),
                            ("refunded", "Refunded"),
                        ],
                        default="pending_payment",
                        max_length=20,
                    ),
                ),
                ("payment_reference", models.CharField(blank=True, max_length=200)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "checkout_session",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="order",
                        to="commerce.checkoutsession",
                    ),
                ),
            ],
            options={
                "verbose_name": "Order",
                "verbose_name_plural": "Orders",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="OrderStatusLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("from_status", models.CharField(max_length=20)),
                ("to_status", models.CharField(max_length=20)),
                ("actor", models.CharField(default="system", max_length=200)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="status_logs",
                        to="commerce.order",
                    ),
                ),
            ],
            options={
                "verbose_name": "Order Status Log",
                "verbose_name_plural": "Order Status Logs",
                "ordering": ["created_at"],
                "default_permissions": ("view",),
            },
        ),
    ]
