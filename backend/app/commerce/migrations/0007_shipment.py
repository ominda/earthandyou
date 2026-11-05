from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("commerce", "0006_shippingrate"),
    ]

    operations = [
        migrations.CreateModel(
            name="Shipment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="shipment",
                        to="commerce.order",
                    ),
                ),
                ("carrier", models.CharField(max_length=100)),
                ("tracking_number", models.CharField(blank=True, max_length=200)),
                ("tracking_url", models.URLField(blank=True, max_length=500)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("dispatched", "Dispatched"),
                            ("in_transit", "In Transit"),
                            ("delivered", "Delivered"),
                            ("returned", "Returned"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("estimated_delivery_date", models.DateField(blank=True, null=True)),
                ("actual_delivery_date", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Shipment",
                "verbose_name_plural": "Shipments",
                "ordering": ["-created_at"],
            },
        ),
    ]
