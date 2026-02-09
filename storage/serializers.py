"""
Serializers for media/upload endpoints
"""

from rest_framework import serializers


class RequestPresignedURLSerializer(serializers.Serializer):
    """
    Serializer for requesting presigned URL for file upload

    Example for avatars:
    {
        "filename": "avatar.jpg",
        "file_size": 2048576,
        "mime_type": "image/jpeg",
        "category": "avatars"
    }

    Example for covers:
    {
        "filename": "cover.jpg",
        "file_size": 3145728,
        "mime_type": "image/jpeg",
        "category": "covers"
    }

    Example for tests:
    {
        "filename": "listening_part1.mp3",
        "file_size": 5242880,
        "mime_type": "audio/mpeg",
        "category": "tests",
        "test_id": 5
    }
    """

    filename = serializers.CharField(
        max_length=255, help_text="Original filename (e.g., avatar.jpg, listening.mp3)"
    )
    file_size = serializers.IntegerField(
        min_value=1,
        max_value=50 * 1024 * 1024,
        help_text="File size in bytes (max 50MB)",
    )
    mime_type = serializers.CharField(
        max_length=100, help_text="MIME type (e.g., image/jpeg, audio/mpeg)"
    )
    category = serializers.ChoiceField(
        choices=["avatars", "covers", "credentials", "tests"],
        help_text="File category: 'avatars', 'covers', 'credentials', or 'tests'",
    )
    test_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Test ID (required if category='tests')",
    )

    def validate(self, data):
        """Validate test_id for tests category"""
        category = data.get("category")
        if category == "tests":
            if "test_id" not in data or data["test_id"] is None:
                raise serializers.ValidationError(
                    {"test_id": "test_id is required when category is tests"}
                )
        return data


class ConfirmUploadSerializer(serializers.Serializer):
    """
    Serializer for confirming file upload completion

    Example for avatars:
    {
        "key": "media/users/avatars/user_123/uuid.jpg",
        "file_size": 2048576,
        "mime_type": "image/jpeg",
        "etag": "abc123def456"
    }

    Example for tests:
    {
        "key": "media/tests/test_5/uuid.mp3",
        "file_size": 5242880,
        "mime_type": "audio/mpeg",
        "etag": "abc123def456"
    }
    """

    key = serializers.CharField(
        max_length=1024, help_text="S3 object key returned from presigned URL"
    )
    file_size = serializers.IntegerField(
        min_value=1, help_text="Actual uploaded file size"
    )
    mime_type = serializers.CharField(
        max_length=100, help_text="Actual MIME type of uploaded file"
    )
    etag = serializers.CharField(
        max_length=255, help_text="ETag from S3 response (for integrity check)"
    )


class PresignedURLResponseSerializer(serializers.Serializer):
    """
    Response serializer for presigned URL endpoint

    Example:
    {
        "key": "media/users/avatars/user_123/uuid.jpg",
        "url": "http://minio:9000/englishapp",
        "fields": {
            "policy": "...",
            "x-amz-credential": "...",
            "x-amz-signature": "...",
            ...
        },
        "expiry": 900
    }
    """

    key = serializers.CharField()
    url = serializers.CharField()
    fields = serializers.JSONField()
    expiry = serializers.IntegerField()


class UploadConfirmationResponseSerializer(serializers.Serializer):
    """
    Response serializer for upload confirmation

    Example:
    {
        "success": true,
        "message": "File uploaded successfully",
        "file_url": "http://minio:9000/englishapp/media/users/avatars/user_123/uuid.jpg"
    }
    """

    success = serializers.BooleanField()
    message = serializers.CharField()
    file_url = serializers.CharField(required=False)
