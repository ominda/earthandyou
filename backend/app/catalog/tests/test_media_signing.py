from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from catalog.services.media_signing import generate_signed_url, generate_signed_urls

SIGN_URL = "/api/v1/catalog/media/sign/"


class MediaSigningServiceTest(TestCase):

    @override_settings(MEDIA_S3_BUCKET="")
    def test_returns_none_when_bucket_not_configured(self):
        result = generate_signed_url("media/gems/test/01.jpg")
        self.assertIsNone(result)

    @override_settings(MEDIA_S3_BUCKET="test-bucket", MEDIA_SIGNED_URL_EXPIRY_SECONDS=3600)
    @patch("catalog.services.media_signing.boto3.client")
    def test_returns_signed_url(self, mock_boto_client):
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = "https://s3.amazonaws.com/signed"
        mock_boto_client.return_value = mock_s3

        result = generate_signed_url("media/gems/test/01.jpg")

        self.assertEqual(result, "https://s3.amazonaws.com/signed")
        mock_s3.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "media/gems/test/01.jpg"},
            ExpiresIn=3600,
        )

    @override_settings(MEDIA_S3_BUCKET="test-bucket")
    @patch("catalog.services.media_signing.boto3.client")
    def test_returns_none_on_client_error(self, mock_boto_client):
        from botocore.exceptions import ClientError
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "get_object"
        )
        mock_boto_client.return_value = mock_s3

        result = generate_signed_url("media/gems/missing.jpg")
        self.assertIsNone(result)

    @override_settings(MEDIA_S3_BUCKET="test-bucket")
    @patch("catalog.services.media_signing.boto3.client")
    def test_generate_signed_urls_batch(self, mock_boto_client):
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.side_effect = lambda op, Params, ExpiresIn: f"https://signed/{Params['Key']}"
        mock_boto_client.return_value = mock_s3

        keys = ["media/01.jpg", "media/02.jpg"]
        result = generate_signed_urls(keys)

        self.assertEqual(result["media/01.jpg"], "https://signed/media/01.jpg")
        self.assertEqual(result["media/02.jpg"], "https://signed/media/02.jpg")


class MediaSignedUrlViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    @override_settings(MEDIA_S3_BUCKET="")
    def test_returns_200_with_null_urls_when_no_bucket(self):
        response = self.client.post(SIGN_URL, {"keys": ["media/01.jpg"]}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["signed_urls"]["media/01.jpg"])

    @override_settings(MEDIA_S3_BUCKET="test-bucket")
    @patch("catalog.views.generate_signed_urls")
    def test_returns_signed_urls(self, mock_sign):
        mock_sign.return_value = {"media/01.jpg": "https://signed/01.jpg"}
        response = self.client.post(SIGN_URL, {"keys": ["media/01.jpg"]}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["signed_urls"]["media/01.jpg"], "https://signed/01.jpg")

    def test_missing_keys_field_returns_empty(self):
        response = self.client.post(SIGN_URL, {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["signed_urls"], {})

    def test_keys_not_a_list_returns_400(self):
        response = self.client.post(SIGN_URL, {"keys": "media/01.jpg"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_exceeding_max_keys_returns_400(self):
        keys = [f"media/{i}.jpg" for i in range(21)]
        response = self.client.post(SIGN_URL, {"keys": keys}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("20", response.data["detail"])

    def test_empty_string_key_returns_400(self):
        response = self.client.post(SIGN_URL, {"keys": ["media/01.jpg", ""]}, format="json")
        self.assertEqual(response.status_code, 400)

    @override_settings(MEDIA_S3_BUCKET="test-bucket")
    @patch("catalog.views.generate_signed_urls")
    def test_multiple_keys_all_returned(self, mock_sign):
        keys = ["media/01.jpg", "media/02.jpg", "certs/report.pdf"]
        mock_sign.return_value = {k: f"https://signed/{k}" for k in keys}
        response = self.client.post(SIGN_URL, {"keys": keys}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["signed_urls"]), 3)
