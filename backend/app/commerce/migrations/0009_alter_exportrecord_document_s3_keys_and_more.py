from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("commerce", "0008_exportrecord"),
    ]

    operations = [
        migrations.AlterField(
            model_name="exportrecord",
            name="document_s3_keys",
            field=models.TextField(
                blank=True,
                help_text="S3 object keys for export documents, one per line",
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="provider_reference",
            field=models.CharField(
                blank=True,
                help_text="Transaction ID or reference returned by the provider",
                max_length=200,
            ),
        ),
    ]
