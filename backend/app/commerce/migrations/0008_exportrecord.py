from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("commerce", "0007_shipment"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExportRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="export_record",
                        to="commerce.order",
                    ),
                ),
                ("export_permit_number", models.CharField(blank=True, max_length=100)),
                ("customs_declaration_number", models.CharField(blank=True, max_length=100)),
                ("declared_value_usd", models.DecimalField(decimal_places=2, max_digits=12)),
                ("destination_country", models.CharField(max_length=100)),
                (
                    "compliance_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("cleared", "Cleared"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("document_s3_keys", models.TextField(blank=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Export Record",
                "verbose_name_plural": "Export Records",
                "ordering": ["-created_at"],
            },
        ),
    ]
