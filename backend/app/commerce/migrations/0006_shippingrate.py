from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("commerce", "0005_refund"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShippingRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "value_tier",
                    models.CharField(
                        choices=[
                            ("standard", "Standard"),
                            ("premium", "Premium"),
                            ("luxury", "Luxury"),
                            ("ultra_luxury", "Ultra Luxury"),
                        ],
                        max_length=20,
                        unique=True,
                    ),
                ),
                ("rate_usd", models.DecimalField(decimal_places=2, max_digits=10)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Shipping Rate",
                "verbose_name_plural": "Shipping Rates",
                "ordering": ["value_tier"],
            },
        ),
    ]
