"""
S3/MinIO Presigned URL utilities
"""

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from datetime import timedelta


class S3PresignedURLManager:
    """Manager for generating presigned URLs for S3/MinIO"""

    ALLOWED_MIME_TYPES = {
        "avatars": ["image/jpeg", "image/png"],
        "tests": ["image/jpeg", "image/png", "video/mp4", "audio/mpeg", "text/html"],
    }

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    PRESIGNED_URL_EXPIRY = 900  # 15 minutes

    def __init__(self):
        # Get AWS settings with fallback defaults
        self.endpoint_url = getattr(
            settings, "AWS_S3_ENDPOINT_URL", "http://minio:9000"
        )
        self.client_endpoint_url = getattr(
            settings, "AWS_S3_CLIENT_ENDPOINT_URL", "http://localhost:9000"
        )
        access_key = getattr(settings, "AWS_ACCESS_KEY_ID", "minio")
        secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", "minio123")
        region_name = getattr(settings, "AWS_S3_REGION_NAME", "us-east-1")
        use_ssl = getattr(settings, "AWS_S3_USE_SSL", False)
        bucket_name = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "englishapp")

        # Backend client: Django → MinIO via internal Docker network (minio:9000)
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
            use_ssl=use_ssl,
        )

        # Presigned client: Generate signatures for browser → MinIO via localhost:9000
        # Browser can reach MinIO via localhost:9000, so signature must be for that endpoint
        self.s3_presigned_client = boto3.client(
            "s3",
            endpoint_url=self.client_endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
            use_ssl=use_ssl,
        )

        self.bucket_name = bucket_name

    def validate_mime_type(self, mime_type: str) -> bool:
        """Validate if MIME type is allowed"""
        for category, allowed_types in self.ALLOWED_MIME_TYPES.items():
            if mime_type in allowed_types:
                return True
        return False

    def validate_file_size(self, file_size: int) -> bool:
        """Validate if file size is within limits"""
        return 0 < file_size <= self.MAX_FILE_SIZE

    def generate_presigned_post(
        self,
        request=None,
        key: str = None,
        file_size: int = None,
        mime_type: str = None,
    ):
        """
        Generate presigned POST URL and form fields for direct S3 upload
        Uses s3_presigned_client to sign with localhost:9000 endpoint
        so signature is valid when browser accesses via localhost:9000.

        Args:
            request: Django request object (used to get client's base URL)
            key: S3 object key (path)
            file_size: Expected file size in bytes
            mime_type: Expected MIME type

        Returns:
            dict: {
                'url': presigned_post_url,
                'fields': form_fields_dict,
                'key': object_key,
                'expiry': 900
            }

        Raises:
            ValueError: If validation fails
            ClientError: If S3 operation fails
        """
        if not self.validate_file_size(file_size):
            raise ValueError(
                f"File size must be between 1 and {self.MAX_FILE_SIZE} bytes"
            )

        if not self.validate_mime_type(mime_type):
            raise ValueError(f"MIME type {mime_type} not allowed")

        try:
            # Use s3_presigned_client to generate POST data signed with localhost:9000
            # Browser will POST to localhost:9000, so signature must match that endpoint
            post_data = self.s3_presigned_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=key,
                Fields={
                    "Content-Type": mime_type,
                },
                Conditions=[
                    {"Content-Type": mime_type},
                    ["content-length-range", 0, self.MAX_FILE_SIZE],
                ],
                ExpiresIn=self.PRESIGNED_URL_EXPIRY,
            )

            return {
                "url": post_data["url"],
                "fields": post_data["fields"],
                "key": key,
                "expiry": self.PRESIGNED_URL_EXPIRY,
            }

        except ClientError as e:
            raise ClientError(e.response, "generate_presigned_post")

    def get_object_metadata(self, key: str):
        """
        Get object metadata from S3 to verify upload

        Args:
            key: S3 object key

        Returns:
            dict: {
                'size': file_size,
                'etag': etag,
                'content_type': mime_type,
                'last_modified': datetime,
                'exists': bool
            }
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)

            return {
                "size": response["ContentLength"],
                "etag": response["ETag"].strip('"'),  # Remove quotes
                "content_type": response.get("ContentType", "unknown"),
                "last_modified": response["LastModified"],
                "exists": True,
            }

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return {"exists": False}
            raise

    def delete_object(self, key: str):
        """Delete object from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def generate_file_key(
        self, category: str, user_id, filename: str, test_id=None, part=None
    ) -> str:
        """
        Generate S3 object key with proper path structure

        Args:
            category: 'avatars' or 'tests'
            user_id: User ID or UUID
            filename: Original filename
            test_id: Test ID (required if category='tests')
            part: Test part number (required if category='tests')

        Returns:
            S3 key:
            - avatars: media/avatars/user_id/unique_filename
            - tests: media/tests/test_id/part{part}/unique_filename
        """
        import uuid
        import os

        # Generate unique name to avoid collisions
        name, ext = os.path.splitext(filename)
        unique_filename = f"{uuid.uuid4()}{ext}"

        if category == "tests":
            if test_id is None or part is None:
                raise ValueError("test_id and part are required for tests category")
            return f"media/tests/{test_id}/part{part}/{unique_filename}"
        else:
            # avatars and other categories
            return f"media/{category}/{user_id}/{unique_filename}"
