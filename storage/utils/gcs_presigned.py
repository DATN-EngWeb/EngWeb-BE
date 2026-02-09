"""
GCS Presigned URL utilities
"""

from google.cloud import storage
from google.oauth2 import service_account
from django.conf import settings
from datetime import timedelta, datetime
import uuid
import os
import logging

logger = logging.getLogger(__name__)


class GCSPresignedURLManager:
    """Manager for generating signed URLs for GCS"""

    ALLOWED_MIME_TYPES = {
        "avatars": ["image/jpeg", "image/png"],
        "covers": ["image/jpeg", "image/png"],
        "credentials": ["application/pdf", "image/jpeg", "image/png"],
        "tests": ["image/jpeg", "image/png", "video/mp4", "audio/mpeg", "text/html"],
    }

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    PRESIGNED_URL_EXPIRY = 900  # 15 minutes

    def __init__(self):
        # Get GCS settings
        self.bucket_name = getattr(settings, "GCS_BUCKET_NAME", "")
        self.project_id = getattr(settings, "GCS_PROJECT_ID", "")
        self.public_base_url = getattr(settings, "GCS_PUBLIC_BASE_URL", "")

        # Initialize GCS client with explicit service account credentials
        # This is required for generating signed URLs
        credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        
        if credentials_path and os.path.exists(credentials_path):
            # Load credentials from service account key file
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            self.client = storage.Client(
                project=self.project_id,
                credentials=self.credentials
            )
            logger.info(f"GCS client initialized with service account from: {credentials_path}")
        else:
            # Fallback to default credentials (may not work for signed URLs)
            self.credentials = None
            self.client = storage.Client(project=self.project_id)
            logger.warning(
                "GOOGLE_APPLICATION_CREDENTIALS not found or file doesn't exist. "
                "Signed URLs may not work properly."
            )

        # Get bucket reference
        try:
            self.bucket = self.client.bucket(self.bucket_name)
            logger.info(f"GCS bucket '{self.bucket_name}' reference created")
        except Exception as e:
            logger.warning(f"GCS bucket '{self.bucket_name}' may not be accessible: {str(e)}")
            self.bucket = self.client.bucket(self.bucket_name)

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
        Generate signed URL for direct GCS upload
        GCS uses signed URLs for PUT requests, but we can create a form-like structure

        Args:
            request: Django request object (used to get client's base URL)
            key: GCS object key (path)
            file_size: Expected file size in bytes
            mime_type: Expected MIME type

        Returns:
            dict: {
                'url': signed_url,
                'fields': form_fields_dict,
                'key': object_key,
                'expiry': 900
            }

        Raises:
            ValueError: If validation fails
            Exception: If GCS operation fails
        """
        if not self.validate_file_size(file_size):
            raise ValueError(
                f"File size must be between 1 and {self.MAX_FILE_SIZE} bytes"
            )

        if not self.validate_mime_type(mime_type):
            raise ValueError(f"MIME type {mime_type} not allowed")

        try:
            blob = self.bucket.blob(key)

            # Generate signed URL for PUT request
            # For GCS, we need to explicitly pass credentials if available
            sign_kwargs = {
                "version": "v4",
                "expiration": timedelta(seconds=self.PRESIGNED_URL_EXPIRY),
                "method": "PUT",
                "content_type": mime_type,
            }
            
            # If we have service account credentials, use them for signing
            if self.credentials:
                sign_kwargs["credentials"] = self.credentials
            
            signed_url = blob.generate_signed_url(**sign_kwargs)
            
            logger.info(f"Generated signed URL for key: {key}")

            # For GCS, we need to provide the signed URL and required headers
            # The client will use PUT with the signed URL
            fields = {
                "Content-Type": mime_type,
            }

            return {
                "url": signed_url,
                "fields": fields,
                "key": key,
                "expiry": self.PRESIGNED_URL_EXPIRY,
            }

        except Exception as e:
            raise Exception(f"Failed to generate signed URL: {str(e)}")

    def get_object_metadata(self, key: str):
        """
        Get object metadata from GCS to verify upload

        Args:
            key: GCS object key

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
            blob = self.bucket.blob(key)
            blob.reload()

            return {
                "size": blob.size,
                "etag": blob.etag,
                "content_type": blob.content_type,
                "last_modified": blob.updated,
                "exists": True,
            }

        except Exception as e:
            if "404" in str(e) or "does not exist" in str(e):
                return {"exists": False}
            raise

    def delete_object(self, key: str):
        """Delete object from GCS"""
        try:
            blob = self.bucket.blob(key)
            blob.delete()
            return True
        except Exception:
            return False

    def delete_folder(self, prefix: str):
        """
        Delete all objects in a folder (with given prefix) from GCS
        
        Args:
            prefix: Folder prefix (e.g., 'media/tests/1/part1/')
        
        Returns:
            Tuple of (success_count, total_count)
        """
        try:
            # Ensure prefix ends with /
            if prefix and not prefix.endswith('/'):
                prefix += '/'
            
            # List and delete all objects with this prefix
            blobs = list(self.bucket.list_blobs(prefix=prefix))
            total_count = len(blobs)
            success_count = 0
            
            for blob in blobs:
                try:
                    blob.delete()
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete blob {blob.name}: {e}")
            
            logger.info(f"Deleted {success_count}/{total_count} objects from folder: {prefix}")
            return (success_count, total_count)
        except Exception as e:
            logger.error(f"Error deleting folder {prefix}: {e}")
            return (0, 0)

    def generate_file_key(
        self, category: str, user_id, filename: str, test_id=None
    ) -> str:
        """
        Generate GCS object key with proper path structure

        Args:
            category: 'avatars', 'covers', 'credentials', or 'tests'
            user_id: User ID or UUID
            filename: Original filename
            test_id: Test ID (required if category='tests')

        Returns:
            GCS key:
            - avatars: media/users/avatars/user_id/unique_filename
            - covers: media/users/covers/user_id/unique_filename
            - credentials: media/teachers/credentials/user_id/unique_filename
            - tests: media/tests/test_{test_id}/unique_filename (all test files in one folder)
        """
        # Generate unique name to avoid collisions
        name, ext = os.path.splitext(filename)
        unique_filename = f"{uuid.uuid4()}{ext}"

        if category == "tests":
            if test_id is None:
                raise ValueError("test_id is required for tests category")
            return f"media/tests/test_{test_id}/{unique_filename}"
        elif category == "avatars":
            # avatars category: use users/avatars path
            return f"media/users/avatars/{user_id}/{unique_filename}"
        elif category == "covers":
            # covers category: use users/covers path
            return f"media/users/covers/{user_id}/{unique_filename}"
        elif category == "credentials":
            # credentials category: use teachers/credentials path
            return f"media/teachers/credentials/{user_id}/{unique_filename}"
        else:
            # other categories (if any in the future)
            return f"media/{category}/{user_id}/{unique_filename}"