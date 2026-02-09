"""Views for storage/file endpoints with signed URLs (GCS)"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import serializers
from tests.models import Test

from .serializers import (
    RequestPresignedURLSerializer,
    ConfirmUploadSerializer,
    PresignedURLResponseSerializer,
    UploadConfirmationResponseSerializer,
)
from .utils.gcs_presigned import GCSPresignedURLManager


# class StorageRateThrottle(UserRateThrottle):
#     """Rate limit: 10 storage requests per minute"""

#     scope = "storage"
#     rate = "10/min"


class RequestPresignedURLView(generics.CreateAPIView):
    """Request signed URL for direct GCS upload"""

    serializer_class = RequestPresignedURLSerializer
    permission_classes = [IsAuthenticated]
    # throttle_classes = [StorageRateThrottle]

    def get_gcs_manager(self):
        """Lazy-load GCSPresignedURLManager"""
        if not hasattr(self, "_gcs_manager"):
            self._gcs_manager = GCSPresignedURLManager()
        return self._gcs_manager

    @extend_schema(
        summary="Yêu cầu URL được ký (Signed URL)",
        description=(
            "Yêu cầu một URL được ký để tải file trực tiếp lên GCS.\n\n"
            "**Các trường yêu cầu (Required fields):**\n"
            "- `filename` - Tên file gốc (VD: avatar.jpg, listening.mp3)\n"
            "- `file_size` - Kích thước file (bytes, tối đa 50MB)\n"
            "- `mime_type` - Loại file MIME (VD: image/jpeg, audio/mpeg)\n"
            "- `category` - Danh mục file ('avatars', 'covers', 'credentials', hoặc 'tests')\n\n"
            "**Các trường tùy chọn (Optional fields):**\n"
            "- `test_id` - ID bài kiểm tra (tùy chọn, nhưng **bắt buộc** khi category = 'tests')\n\n"
            "**Các danh mục (category):**\n"
            "- `avatars` - Ảnh đại diện người dùng (JPEG, PNG)\n"
            "- `covers` - Ảnh bìa người dùng (JPEG, PNG)\n"
            "- `credentials` - Chứng chỉ/bằng cấp giáo viên (PDF, JPEG, PNG)\n"
            "- `tests` - File kiểm tra (JPEG, PNG, MP4, MPEG)\n\n"
            "**Cấu trúc folder:**\n"
            "- Tất cả files của test: media/tests/test_{test_id}/filename\n\n"
            "**Quy trình:**\n"
            "1. FE gửi yêu cầu với thông tin file\n"
            "2. BE trả về signed URL + headers cần thiết\n"
            "3. FE upload file trực tiếp đến GCS bằng PUT request\n"
            "4. FE gửi confirmation sau khi tải xong\n\n"
            "**Giới hạn:**\n"
            "- Kích thước file: 50MB tối đa\n"
            "- Hết hạn URL: 15 phút"
        ),
        tags=["storage"],
        request=RequestPresignedURLSerializer,
        responses={
            201: OpenApiResponse(
                description="Presigned URL generated successfully",
                response=PresignedURLResponseSerializer,
            ),
            400: OpenApiResponse(
                description="Invalid request data or MIME type not allowed",
                response=inline_serializer(
                    name="ErrorResponse",
                    fields={"detail": serializers.CharField()},
                ),
            ),
            500: OpenApiResponse(
                description="Server error generating presigned URL",
                response=inline_serializer(
                    name="ServerErrorResponse",
                    fields={"detail": serializers.CharField()},
                ),
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        """Handle POST request for presigned URL"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            filename = serializer.validated_data["filename"]
            file_size = serializer.validated_data["file_size"]
            mime_type = serializer.validated_data["mime_type"]
            category = serializer.validated_data["category"]
            test_id = serializer.validated_data.get("test_id")

            if category == "tests" and test_id is not None:
                if not Test.objects.filter(id=test_id).exists():
                    return Response(
                        {"detail": f"Test with id {test_id} does not exist."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            s3_key = self.get_gcs_manager().generate_file_key(
                category=category,
                user_id=request.user.file_storage_uuid,
                filename=filename,
                test_id=test_id,
            )

            # Generate signed URL
            presigned_data = self.get_gcs_manager().generate_presigned_post(
                request=request, key=s3_key, file_size=file_size, mime_type=mime_type
            )

            # Response
            response_serializer = PresignedURLResponseSerializer(presigned_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"detail": "Failed to generate upload URL"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ConfirmUploadView(generics.CreateAPIView):
    """
    Confirm file upload and validate metadata on GCS
    """

    serializer_class = ConfirmUploadSerializer
    permission_classes = [IsAuthenticated]
    # throttle_classes = [StorageRateThrottle]

    def get_gcs_manager(self):
        """Lazy-load GCSPresignedURLManager to avoid issues during schema generation"""
        if not hasattr(self, "_gcs_manager"):
            self._gcs_manager = GCSPresignedURLManager()
        return self._gcs_manager

    @extend_schema(
        summary="Xác nhận tải file thành công",
        description=(
            "Xác nhận file đã được tải lên GCS thành công và xác thực metadata.\n\n"
            "**Quy trình xác nhận:**\n"
            "1. Kiểm tra file có tồn tại trên GCS\n"
            "2. Xác thực kích thước file khớp với yêu cầu\n"
            "3. Xác thực MIME type hợp lệ\n"
            "4. Trả về URL công khai của file\n\n"
            "**Lỗi có thể xảy ra:**\n"
            "- File không tìm thấy trên GCS\n"
            "- Kích thước file không khớp (upload chưa hoàn tất)\n"
            "- MIME type không được hỗ trợ"
        ),
        tags=["storage"],
        request=ConfirmUploadSerializer,
        responses={
            201: OpenApiResponse(
                description="Upload confirmed successfully",
                response=UploadConfirmationResponseSerializer,
            ),
            400: OpenApiResponse(
                description="File validation failed",
                response=inline_serializer(
                    name="ConfirmErrorResponse",
                    fields={"detail": serializers.CharField()},
                ),
            ),
            500: OpenApiResponse(
                description="Server error confirming upload",
                response=inline_serializer(
                    name="ConfirmServerErrorResponse",
                    fields={"detail": serializers.CharField()},
                ),
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        """Handle POST request to confirm upload"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Extract data
            s3_key = serializer.validated_data["key"]
            file_size = serializer.validated_data["file_size"]
            mime_type = serializer.validated_data["mime_type"]
            etag = serializer.validated_data["etag"]

            # Verify file exists on GCS
            metadata = self.get_gcs_manager().get_object_metadata(s3_key)

            if not metadata.get("exists"):
                return Response(
                    {"detail": "File not found on GCS. Upload may have failed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate size
            if metadata["size"] != file_size:
                return Response(
                    {"detail": "File size mismatch. File may be corrupted."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate MIME type
            if not self.get_gcs_manager().validate_mime_type(mime_type):
                return Response(
                    {"detail": f"Invalid MIME type: {mime_type}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Generate public URL
            file_url = f"{self.get_gcs_manager().public_base_url}/{self.get_gcs_manager().bucket_name}/{s3_key}"

            # Response
            response_data = {
                "success": True,
                "message": "File uploaded successfully",
                "file_url": file_url,
            }
            response_serializer = UploadConfirmationResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"detail": "Failed to confirm upload"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
