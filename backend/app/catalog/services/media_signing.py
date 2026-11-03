import logging
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


def generate_signed_url(s3_key: str) -> str | None:
    """
    Generate a pre-signed S3 URL for the given object key.

    Returns None if:
    - MEDIA_S3_BUCKET is not configured (local dev)
    - boto3 raises any error (credentials missing, key not found, etc.)

    Expiry is controlled by MEDIA_SIGNED_URL_EXPIRY_SECONDS (default 3600).
    """
    bucket = settings.MEDIA_S3_BUCKET
    if not bucket:
        return None

    expiry = settings.MEDIA_SIGNED_URL_EXPIRY_SECONDS

    try:
        client = boto3.client("s3")
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": s3_key},
            ExpiresIn=expiry,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.warning("Failed to generate signed URL for key '%s': %s", s3_key, exc)
        return None


def generate_signed_urls(s3_keys: list[str]) -> dict[str, str | None]:
    """
    Generate signed URLs for a list of S3 keys.
    Returns a dict mapping each key to its signed URL (or None on failure).
    """
    return {key: generate_signed_url(key) for key in s3_keys}
