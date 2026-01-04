from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.parsers import BaseParser
from rest_framework.views import APIView
import io

from django.http.request import HttpRequest
from django.http.multipartparser import MultiPartParser
from django.core.files.uploadhandler import MemoryFileUploadHandler

from ..models import Test
from ..serializers.serializers_receptive_test import ReceptiveTestCreateSerializer
from ..permissions import IsTeacher
from accounts.utils import get_or_create_file_storage_uuid
from ..utils.chunked_upload import (
    save_chunk,
    merge_chunks,
    cleanup_upload_session,
    get_missing_chunks,
)

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter,
)


class ReceptiveTestCreateView(generics.CreateAPIView):
    """
    Unified view for uploading Receptive Test content (Reading & Listening) - Chunked
    """

    permission_classes = [IsTeacher]
    parser_classes = (BaseParser,)  # Raw binary parser

    @extend_schema(
        summary="Tải lên nội dung bài kiểm tra tiếp nhận theo từng chunk",
        description=(
            "Tải lên nội dung bài kiểm tra tiếp nhận (Reading & Listening) theo từng chunk nhị phân.\n\n"
            "**Quy trình hoạt động:**\n"
            "1. Client tạo payload multipart (data + file ảnh/âm thanh) bằng FormData\n"
            "2. Client chia payload thành các chunk nhỏ (ví dụ: 5MB mỗi chunk)\n"
            "3. Client tải lên từng chunk theo thứ tự dưới dạng nhị phân (application/octet-stream)\n"
            "4. Server lưu trữ các chunk tạm thời và kiểm tra tính hoàn chỉnh\n"
            "5. Khi chunk cuối cùng đến: Server kiểm tra tất cả chunks → gộp → phân tích multipart → tạo bài kiểm tra → dọn dẹp\n\n"
            "**Xác thực chunk:**\n"
            "- Khi X-Is-Complete=true, server xác minh tất cả chunks (1-total_chunks) đã được nhận\n"
            "- Nếu thiếu chunk nào, trả về 400 kèm danh sách chunk bị thiếu\n"
            "- Client phải gửi lại chunk bị thiếu, sau đó thử lại chunk cuối cùng\n\n"
            "**Headers yêu cầu:**\n"
            "- `X-Upload-ID`: Định danh phiên upload duy nhất (giống nhau cho tất cả chunks)\n"
            "- `X-Chunk-Number`: Số thứ tự chunk hiện tại (bắt đầu từ 1, ví dụ: 1, 2, 3...)\n"
            "- `X-Total-Chunks`: Tổng số chunks dự kiến\n"
            "- `X-Is-Complete`: Đặt thành 'true' CHỈ trên chunk cuối cùng\n"
            "- `Content-Type`: Luôn là 'application/octet-stream'\n"
            "- `Authorization`: Bearer token\n\n"
            "**Ví dụ: Tải lên 3 chunks với xác thực**\n"
            "```\n"
            "1. Gửi Chunk 1/3\n"
            "   POST /api/tests/receptive/2\n"
            "   X-Upload-ID: sess_abc123\n"
            "   X-Chunk-Number: 1\n"
            "   X-Total-Chunks: 3\n"
            "   X-Is-Complete: false\n"
            "   → 202 Accepted\n\n"
            "2. Gửi Chunk 2/3\n"
            "   POST /api/tests/receptive/2\n"
            "   X-Upload-ID: sess_abc123\n"
            "   X-Chunk-Number: 2\n"
            "   X-Total-Chunks: 3\n"
            "   X-Is-Complete: false\n"
            "   → 202 Accepted\n\n"
            "3. Gửi Chunk 3/3 (cuối cùng)\n"
            "   POST /api/tests/receptive/2\n"
            "   X-Upload-ID: sess_abc123\n"
            "   X-Chunk-Number: 3\n"
            "   X-Total-Chunks: 3\n"
            "   X-Is-Complete: true\n"
            "   → Server xác minh tất cả 3 chunks có mặt\n"
            "   → 201 Created\n\n"
            "Hoặc nếu chunk 2 bị mất:\n"
            "   → 400 Bad Request\n"
            "   {\"missing_chunks\": [2], \"message\": \"Please resend chunks: [2]\"}\n"
            "   Client gửi lại chunk 2, sau đó thử lại chunk 3\n"
            "```\n"
        ),
        tags=["receptive-tests"],
        parameters=[
            OpenApiParameter(
                name="test_id",
                location=OpenApiParameter.PATH,
                type=int,
                description="ID của bài kiểm tra để tải lên nội dung",
            ),
        ],
        request=None,
        responses={
            202: OpenApiResponse(
                description="Chunk trung gian được nhận, chờ chunk tiếp theo",
                response={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "example": "chunk_received"},
                        "chunk_number": {"type": "integer", "example": 1},
                        "upload_id": {"type": "string", "example": "sess_abc123"},
                        "message": {"type": "string", "example": "Chunk 1/3 received"},
                    },
                },
            ),
            201: OpenApiResponse(
                description="Chunk cuối được nhận, tất cả chunks xác minh, bài kiểm tra tạo thành công",
                response={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "example": "upload_complete"},
                        "test_id": {"type": "integer", "example": 2},
                        "total_score": {"type": "integer", "example": 100},
                        "message": {"type": "string", "example": "Receptive test created successfully"},
                    },
                },
            ),
            400: OpenApiResponse(
                description="Yêu cầu không hợp lệ - headers thiếu, chunk bị thiếu, dữ liệu rỗng hoặc lỗi xác thực",
                response={
                    "type": "object",
                    "properties": {
                        "upload_id": {"type": "string", "example": "sess_abc123"},
                        "detail": {"type": "string"},
                        "missing_chunks": {"type": "array", "items": {"type": "integer"}, "example": [2, 5]},
                        "expected_total": {"type": "integer", "example": 7},
                        "received": {"type": "integer", "example": 5},
                        "message": {"type": "string", "example": "Please resend chunks: [2, 5]"},
                        "chunk_number": {"type": "integer", "example": 2},
                        "required_headers": {"type": "object"},
                        "errors": {"type": "object"},
                        "error_type": {"type": "string"},
                    },
                },
            ),
            404: OpenApiResponse(description="Test ID không tồn tại"),
            403: OpenApiResponse(description="Người dùng không phải giáo viên"),
            500: OpenApiResponse(description="Lỗi máy chủ trong quá trình xử lý chunk hoặc phân tích multipart"),
        },
    )
    def post(self, request, *args, **kwargs):
        """Upload chunk of receptive test content"""
        try:
            test_id = kwargs.get("test_id")

            # Extract headers
            upload_id = request.META.get("HTTP_X_UPLOAD_ID")
            chunk_number = request.META.get("HTTP_X_CHUNK_NUMBER")
            total_chunks = request.META.get("HTTP_X_TOTAL_CHUNKS")
            is_complete = (
                request.META.get("HTTP_X_IS_COMPLETE", "false").lower() == "true"
            )

            # Get raw binary data
            try:
                chunk_data = request.stream.read()
            except Exception as e:
                return Response(
                    {
                        "upload_id": upload_id,
                        "detail": f"Error reading request body: {str(e)}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not chunk_data:
                return Response(
                    {
                        "upload_id": upload_id,
                        "detail": "Request body is empty. Send raw binary chunk data."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate headers
            if not all([upload_id, chunk_number, total_chunks]):
                return Response(
                    {
                        "upload_id": upload_id,
                        "detail": "Missing required headers: X-Upload-ID, X-Chunk-Number, X-Total-Chunks",
                        "required_headers": {
                            "X-Upload-ID": "unique session identifier",
                            "X-Chunk-Number": "current chunk number (1-based)",
                            "X-Total-Chunks": "total number of chunks",
                            "X-Is-Complete": "true only on final chunk (optional)",
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                chunk_number = int(chunk_number)
                total_chunks = int(total_chunks)
            except (ValueError, TypeError):
                return Response(
                   {
                       "upload_id": upload_id,
                       "detail": "X-Chunk-Number and X-Total-Chunks must be integers"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate chunk number
            if chunk_number < 1 or chunk_number > total_chunks:
                return Response(
                    {
                        "upload_id": upload_id,
                        "detail": f"Invalid X-Chunk-Number. Must be 1-{total_chunks}"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verify test exists
            try:
                test = Test.objects.get(id=test_id)
            except Test.DoesNotExist:
                return Response(
                    {"detail": f"Test with id {test_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Save chunk (raw binary) - check return value
            success, chunk_file, error_msg = save_chunk(
                upload_id, chunk_number, chunk_data
            )
            if not success:
                return Response(
                    {
                        "upload_id": upload_id,
                        "chunk_number": chunk_number,
                        "detail": f"Failed to save chunk {chunk_number}: {error_msg}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # If not last chunk, return 202 Accepted
            if not is_complete:
                return Response(
                    {
                        "status": "chunk_received",
                        "chunk_number": chunk_number,
                        "upload_id": upload_id,
                        "message": f"Chunk {chunk_number}/{total_chunks} received",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

            # All chunks received - check for missing chunks first
            missing_chunks = get_missing_chunks(upload_id, total_chunks)
            if missing_chunks:
                return Response(
                    {
                        "upload_id": upload_id,
                        "detail": f"Cannot complete upload - missing {len(missing_chunks)} chunk(s)",
                        "missing_chunks": missing_chunks,
                        "expected_total": total_chunks,
                        "received": total_chunks - len(missing_chunks),
                        "message": f"Please resend chunks: {missing_chunks}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # All chunks received - merge and process
            try:
                merged_data = merge_chunks(upload_id, total_chunks)
            except Exception as e:
                cleanup_upload_session(upload_id)
                return Response(
                    {"detail": f"Failed to merge chunks: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Parse merged multipart form-data
            content_type = request.META.get("CONTENT_TYPE", "")

            # If no boundary in content type, extract from merged data
            if "boundary=" not in content_type:
                merged_data_str = merged_data[:300].decode("utf-8", errors="ignore")
                if merged_data_str.startswith("--"):
                    first_line = merged_data_str.split("\r\n")[0]
                    boundary = first_line.lstrip("-")
                    content_type = f"multipart/form-data; boundary={boundary}"

            fake_request = HttpRequest()
            fake_request.method = "POST"
            fake_request.META = {
                "CONTENT_TYPE": content_type,
                "CONTENT_LENGTH": str(len(merged_data)),
            }

            # Parse multipart data
            try:
                # Create upload handlers for MultiPartParser
                upload_handlers = [MemoryFileUploadHandler()]
                parser = MultiPartParser(
                    fake_request.META, io.BytesIO(merged_data), upload_handlers
                )
                post_data, files_data = parser.parse()
            except Exception as parse_error:
                cleanup_upload_session(upload_id)
                return Response(
                    {
                        "detail": f"Failed to parse multipart data: {str(parse_error)}",
                        "error_type": type(parse_error).__name__,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get user UUID
            try:
                user_uuid = get_or_create_file_storage_uuid(request.user)
            except Exception as e:
                cleanup_upload_session(upload_id)
                return Response(
                    {"detail": f"Failed to get user UUID: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Serialize and create receptive test
            # post_data is a QueryDict, get the 'data' field
            json_data = post_data.get("data")
            if not json_data:
                cleanup_upload_session(upload_id)
                return Response(
                    {"detail": "No 'data' field in multipart payload"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # If json_data is bytes, decode it
            if isinstance(json_data, bytes):
                json_data = json_data.decode("utf-8")

            # Strip any whitespace/CRLF
            json_data = json_data.strip()

            # Try to extract just the valid JSON part by finding the last closing brace/bracket
            # This handles cases where multipart parser includes extra data
            if json_data:
                # Find the position of the last closing brace or bracket
                for i in range(len(json_data) - 1, -1, -1):
                    if json_data[i] in ("}", "]"):
                        json_data = json_data[: i + 1]
                        break

            serializer = ReceptiveTestCreateSerializer(
                data={"data": json_data},
                context={
                    "request": request,
                    "test_id": test_id,
                    "user_uuid": user_uuid,
                    "files": files_data,
                },
            )

            if not serializer.is_valid():
                cleanup_upload_session(upload_id)
                return Response(
                    {"detail": "Validation error", "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create receptive test
            receptive_test = serializer.save()
            cleanup_upload_session(upload_id)

            return Response(
                {
                    "status": "upload_complete",
                    "test_id": receptive_test.test_id,
                    "total_score": receptive_test.total_score,
                    "message": "Receptive test created successfully",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            # Top-level error handler
            return Response(
                {
                    "detail": f"Unexpected error: {str(e)}",
                    "error_type": type(e).__name__,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
