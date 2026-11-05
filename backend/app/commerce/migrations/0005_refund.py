# Generated migration for module 4.8 — Refund model

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("commerce", "0004_payment"),
    ]

    operations = [
        migrations.CreateModel(
            name="Refund",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount_usd", models.DecimalField(decimal_places=2, max_digits=12)),
                ("reason", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=10,
                    ),
                ),
                ("provider_reference", models.CharField(blank=True, max_length=200)),
                ("raw_response", models.JSONField(blank=True, default=dict)),
                ("requested_by", models.CharField(default="system", max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="refund",
                        to="commerce.order",
                    ),
                ),
                (
                    "payment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="refunds",
                        to="commerce.payment",
                    ),
                ),
            ],
            options={
                "verbose_name": "Refund",
                "verbose_name_plural": "Refunds",
                "ordering": ["-created_at"],
            },
        ),
    ]
