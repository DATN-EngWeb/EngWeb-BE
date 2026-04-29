import json

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AssistantConversation, AssistantMessage
from .serializers import (
    AssistantConversationCreateSerializer,
    AssistantConversationDetailSerializer,
    AssistantConversationRenameSerializer,
    AssistantConversationSerializer,
    AssistantSendMessageSerializer,
)
from .utils import (
    call_assistant_model,
    check_and_consume_quota,
    generate_conversation_title,
    get_quota_status,
    normalize_mode,
    release_quota,
)


class AssistantConversationListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Danh sách hội thoại assistant",
        description=(
            "Lấy danh sách các cuộc trò chuyện của người dùng hiện tại.\n\n"
            "### Cách dùng nhanh\n"
            "- `GET` dùng để xem tất cả cuộc trò chuyện chưa lưu trữ.\n"
            "- `POST` dùng để tạo một cuộc trò chuyện mới trước khi gửi tin nhắn.\n\n"
            "### Ghi chú tạo mới\n"
            "- Gửi `mode` để chọn chế độ mặc định của hội thoại.\n"
            "- `level` là mức độ học viên, ví dụ `A2`, `B1`, `intermediate`.\n"
            "- `title` là tùy chọn. Nếu không gửi, hệ thống sẽ tự đặt tên."
        ),
        tags=["assistant"],
        responses={200: AssistantConversationSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Tạo hội thoại assistant mới",
        description=(
            "Tạo một cuộc trò chuyện assistant mới cho người dùng hiện tại.\n\n"
            "### Khi nào dùng\n"
            "- Dùng khi FE cần khởi tạo một phiên chat mới trước khi gửi tin nhắn.\n\n"
            "### Ghi chú\n"
            "- `mode` có thể là `translate`, `grammar`, `vocabulary`, `brainstorm`, hoặc `general`.\n"
            "- Nếu không gửi `title`, hệ thống sẽ đặt `New Chat`.\n"
            "- Nếu không gửi `mode`, hệ thống sẽ dùng `general`."
        ),
        tags=["assistant"],
        request=AssistantConversationCreateSerializer,
        responses={201: AssistantConversationSerializer},
        examples=[
            OpenApiExample(
                name="Tạo chat dịch nghĩa",
                request_only=True,
                value={
                    "title": "Dịch câu này giúp tôi",
                    "mode": "translate",
                    "level": "B1",
                },
            ),
            OpenApiExample(
                name="Tạo chat giải thích ngữ pháp",
                request_only=True,
                value={
                    "title": "Giải thích thì hiện tại hoàn thành",
                    "mode": "grammar",
                    "level": "B1",
                },
            ),
            OpenApiExample(
                name="Tạo chat luyện từ vựng",
                request_only=True,
                value={
                    "title": "Giải thích từ 'get'",
                    "mode": "vocabulary",
                    "level": "A2",
                },
            ),
            OpenApiExample(
                name="Tạo chat brainstorm ý tưởng viết",
                request_only=True,
                value={
                    "title": "Brainstorm ý tưởng viết về chủ đề công nghệ",
                    "mode": "brainstorm",
                    "level": "B2",
                },
            ),
            OpenApiExample(
                name="Tạo chat tổng quát",
                request_only=True,
                value={
                    "mode": "general",
                    "level": "A2",
                },
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Return the full conversation representation (including id)
        return Response(
            AssistantConversationSerializer(instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def get_queryset(self):
        return AssistantConversation.objects.filter(
            user=self.request.user,
            is_archived=False,
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AssistantConversationCreateSerializer
        return AssistantConversationSerializer


class AssistantConversationRetrieveAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AssistantConversationDetailSerializer

    @extend_schema(
        summary="Chi tiết hội thoại assistant",
        description=(
            "Xem chi tiết một hội thoại assistant với một phần tin nhắn gần nhất.\n\n"
            "### Dùng khi nào\n"
            "- Khi FE cần tải lại trang chat.\n"
            "- Khi cần hiển thị lịch sử trao đổi của một cuộc trò chuyện.\n\n"
            "### Tải thêm tin cũ\n"
            "- `limit`: số tin nhắn muốn lấy, mặc định là 30, tối đa 100.\n"
            "- `before_id`: lấy các tin nhắn cũ hơn tin nhắn có id này."
        ),
        tags=["assistant"],
        parameters=[
            OpenApiParameter(name="limit", required=False, type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter(name="before_id", required=False, type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
        ],
        responses={200: AssistantConversationDetailSerializer},
    )
    def get(self, request, *args, **kwargs):
        conversation = self.get_object()
        limit = self._get_limit(request)
        before_id = request.query_params.get("before_id")

        messages_qs = conversation.messages.order_by("-created_at", "-id")
        cursor_message = None

        if before_id:
            try:
                before_id = int(before_id)
            except (TypeError, ValueError):
                return Response({"detail": "before_id must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

            cursor_message = messages_qs.filter(id=before_id).first()
            if cursor_message is None:
                return Response({"detail": "Cursor message not found."}, status=status.HTTP_400_BAD_REQUEST)

            messages_qs = messages_qs.filter(
                Q(created_at__lt=cursor_message.created_at)
                | Q(created_at=cursor_message.created_at, id__lt=cursor_message.id)
            )

        selected_messages = list(messages_qs[:limit])
        selected_messages.reverse()

        messages_meta = self._build_messages_meta(conversation, selected_messages, limit, cursor_message)
        serializer = self.get_serializer(
            conversation,
            context={
                "request": request,
                "messages": selected_messages,
                "messages_meta": messages_meta,
            },
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        return (
            AssistantConversation.objects.filter(
                user=self.request.user,
                is_archived=False,
            )
            .order_by("-last_message_at")
        )

    def _get_limit(self, request):
        raw_limit = request.query_params.get("limit")
        default_limit = 30
        max_limit = 100

        if raw_limit is None or raw_limit == "":
            return default_limit

        try:
            value = int(raw_limit)
        except (TypeError, ValueError):
            return default_limit

        return max(1, min(value, max_limit))

    def _build_messages_meta(self, conversation, selected_messages, limit, cursor_message=None):
        total_count = conversation.messages.count()
        if not selected_messages:
            return {
                "limit": limit,
                "count": 0,
                "total_count": total_count,
                "has_more": False,
                "oldest_id": None,
                "newest_id": None,
                "before_id": cursor_message.id if cursor_message else None,
            }

        oldest_message = selected_messages[0]
        newest_message = selected_messages[-1]

        has_more = conversation.messages.filter(
            Q(created_at__lt=oldest_message.created_at)
            | Q(created_at=oldest_message.created_at, id__lt=oldest_message.id)
        ).exists()

        return {
            "limit": limit,
            "count": len(selected_messages),
            "total_count": total_count,
            "has_more": has_more,
            "oldest_id": oldest_message.id,
            "newest_id": newest_message.id,
            "before_id": cursor_message.id if cursor_message else None,
        }


class AssistantConversationArchiveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Lưu trữ hội thoại assistant",
        description=(
            "Lưu trữ một cuộc trò chuyện assistant.\n\n"
            "### Kết quả\n"
            "- Hội thoại sẽ bị ẩn khỏi danh sách mặc định.\n"
            "- Dữ liệu không bị xóa vĩnh viễn."
        ),
        tags=["assistant"],
        responses={
            204: OpenApiResponse(description="Đã lưu trữ hội thoại"),
            404: OpenApiResponse(description="Không tìm thấy hội thoại"),
        },
    )
    def delete(self, request, conversation_id):
        conversation = AssistantConversation.objects.filter(
            id=conversation_id,
            user=request.user,
            is_archived=False,
        ).first()

        if not conversation:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        conversation.is_archived = True
        conversation.save(update_fields=["is_archived", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssistantConversationRenameAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Đổi tên hội thoại assistant",
        description=(
            "Đổi tên một cuộc trò chuyện assistant.\n\n"
            "### Ghi chú\n"
            "- Chỉ đổi tên hội thoại thuộc về người dùng hiện tại.\n"
            "- Tên mới không được để trống."
        ),
        tags=["assistant"],
        request=AssistantConversationRenameSerializer,
        responses={
            200: AssistantConversationSerializer,
            400: OpenApiResponse(description="Dữ liệu không hợp lệ"),
            404: OpenApiResponse(description="Không tìm thấy hội thoại"),
        },
        examples=[
            OpenApiExample(
                name="Đổi tên hội thoại",
                request_only=True,
                value={
                    "title": "Luyện grammar về thì hiện tại hoàn thành",
                },
            )
        ],
    )
    def patch(self, request, conversation_id):
        serializer = AssistantConversationRenameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = AssistantConversation.objects.filter(
            id=conversation_id,
            user=request.user,
            is_archived=False,
        ).first()

        if not conversation:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        conversation.title = serializer.validated_data["title"].strip()
        conversation.is_title_auto = False
        conversation.save(update_fields=["title", "is_title_auto", "updated_at"])

        return Response(AssistantConversationSerializer(conversation).data, status=status.HTTP_200_OK)


class AssistantQuotaAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Xem quota assistant",
        description=(
            "Xem quota hiện tại của assistant.\n\n"
            "### Ý nghĩa các trường\n"
            "- `remaining`: số tin nhắn còn lại.\n"
            "- `limit`: giới hạn tối đa trong chu kỳ hiện tại.\n"
            "- `reset_at`: thời điểm quota được làm mới."
        ),
        tags=["assistant"],
        responses={
            200: inline_serializer(
                name="AssistantQuotaResponse",
                fields={
                    "remaining": serializers.IntegerField(),
                    "limit": serializers.IntegerField(),
                    "reset_at": serializers.DateTimeField(),
                },
            )
        },
    )
    def get(self, request):
        quota = get_quota_status(request.user)
        return Response(quota, status=status.HTTP_200_OK)


@extend_schema(
    summary="Gửi tin nhắn cho assistant",
    description=(
        "Gửi một tin nhắn đến hội thoại assistant.\n\n"
        "### Quy trình xử lý\n"
        "1. Kiểm tra hội thoại có tồn tại và chưa bị lưu trữ.\n"
        "2. Ghi lại tin nhắn của người dùng.\n"
        "3. Lấy ngữ cảnh ngắn từ các tin nhắn gần nhất trong hội thoại.\n"
        "4. Gọi mô hình AI theo `mode` đang chọn.\n"
        "5. Trả về câu trả lời, thông tin token và quota còn lại.\n\n"
        "### Ghi chú\n"
        "- Nếu không truyền `mode`, hệ thống sẽ dùng `mode` đang gán cho hội thoại.\n"
        "- `context` là một JSON object (tuỳ chọn) chứa các khóa sau:\n"
        "  - `target_language` (string): ngôn ngữ mong muốn cho các phần giải thích (ví dụ: 'Vietnamese', 'English').\n"
        "  - `language` (string): alias cho `target_language`.\n"
        "  - `level` (string): trình độ học viên (ví dụ: 'A2', 'B1').\n"
        "  - `source_text` (string): đoạn văn hoặc câu nguồn liên quan đến yêu cầu.\n"
        "\n"
        "Ví dụ ngắn về `context`: {\"target_language\": \"Vietnamese\", \"level\": \"B1\", \"source_text\": \"I had already finished my homework before dinner.\" }\n"
    ),
    tags=["assistant"],
    request=AssistantSendMessageSerializer,
    responses={
        200: inline_serializer(
            name="AssistantMessageResponse",
            fields={
                "message_id": serializers.IntegerField(),
                "assistant_message_id": serializers.IntegerField(),
                "answer": serializers.JSONField(),
                "mode": serializers.CharField(),
                "usage": inline_serializer(
                    name="AssistantUsageResponse",
                    fields={
                        "prompt_token_count": serializers.IntegerField(allow_null=True),
                        "completion_token_count": serializers.IntegerField(allow_null=True),
                        "total_token_count": serializers.IntegerField(allow_null=True),
                    },
                ),
                "quota": inline_serializer(
                    name="AssistantQuotaEmbeddedResponse",
                    fields={
                        "remaining": serializers.IntegerField(),
                        "limit": serializers.IntegerField(),
                        "reset_at": serializers.DateTimeField(),
                    },
                ),
            },
        ),
        400: OpenApiResponse(description="Dữ liệu không hợp lệ"),
        404: OpenApiResponse(description="Không tìm thấy hội thoại"),
        429: OpenApiResponse(description="Vượt quá quota assistant"),
        502: OpenApiResponse(description="Lỗi từ dịch vụ AI"),
    },
    examples=[
        OpenApiExample(
            name="Dịch câu tiếng Anh",
            request_only=True,
            value={
                "message": "Dịch câu sau sang tiếng Việt: I had already finished my homework before dinner.",
                "mode": "translate",
                "context": {
                    "level": "B1",
                    "source_text": "I had already finished my homework before dinner.",
                },
            },
        ),
        OpenApiExample(
            name="Giải thích ngữ pháp",
            request_only=True,
            value={
                "message": "Giải thích tại sao chúng ta sử dụng thì hiện tại hoàn thành trong câu sau: I have lived here for five years.",
                "mode": "grammar",
                "context": {
                    "level": "B1",
                },
            },
        ),
        OpenApiExample(
            name="Giải thích từ vựng",
            request_only=True,
            value={
                "message": "Từ 'get' có nghĩa là gì trong câu sau: I need to get some sleep?",
                "mode": "vocabulary",
                "context": {
                    "level": "A2",
                },
            },
        ),
        OpenApiExample(
            name="Brainstorm ý tưởng viết",
            request_only=True,
            value={
                "message": "Tôi muốn viết một bài luận về tác động của công nghệ đến cuộc sống hàng ngày. Bạn có thể giúp tôi brainstorm ý tưởng, dàn ý, và từ vựng liên quan không?",
                "mode": "brainstorm",
                "context": {
                    "level": "B2",
                },
            },
        ),
        OpenApiExample(
            name="Hỏi chung",
            request_only=True,
            value={
                "message": "Sự khác nhau giữa 'say' và 'tell'?",
                "mode": "general",
                "context": {
                    "level": "A2",
                },
            },
        ),
    ],
)
class AssistantConversationMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        serializer = AssistantSendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = AssistantConversation.objects.filter(
            id=conversation_id,
            user=request.user,
            is_archived=False,
        ).first()

        if not conversation:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        message_text = serializer.validated_data["message"]
        request_mode = serializer.validated_data.get("mode")
        context = serializer.validated_data.get("context", {})

        mode = normalize_mode(request_mode or conversation.mode)

        memory_limit = max(int(getattr(settings, "ASSISTANT_SHORT_MEMORY_MESSAGES", 6)), 0)
        recent_history = []
        if memory_limit > 0:
            history_qs = (
                conversation.messages.filter(
                    role__in=[AssistantMessage.ROLE_USER, AssistantMessage.ROLE_ASSISTANT],
                    status=AssistantMessage.STATUS_COMPLETED,
                )
                .order_by("-created_at")[:memory_limit]
            )
            import json as _json

            recent_history = []
            for item in reversed(list(history_qs)):
                raw = item.content or ""
                text_for_history = ""
                # If content is JSON string, try to parse and prefer `text` key.
                if raw:
                    try:
                        import json as _json

                        parsed = _json.loads(raw)
                        if isinstance(parsed, dict) and parsed.get("text"):
                            text_for_history = str(parsed.get("text"))
                        else:
                            text_for_history = _json.dumps(parsed, ensure_ascii=False)
                    except Exception:
                        text_for_history = raw

                if not text_for_history:
                    continue

                recent_history.append({"role": item.role, "content": text_for_history})

        allowed, quota_info = check_and_consume_quota(request.user, amount=1, reserve=True)
        if not allowed:
            return Response(
                {
                    "detail": "Assistant quota exceeded.",
                    "quota": {
                        "remaining": quota_info["remaining"],
                        "limit": quota_info["limit"],
                        "reset_at": quota_info["reset_at"],
                    },
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        with transaction.atomic():
            user_message = AssistantMessage.objects.create(
                conversation=conversation,
                role=AssistantMessage.ROLE_USER,
                content=message_text,
                status=AssistantMessage.STATUS_COMPLETED,
            )

            if conversation.is_title_auto and conversation.title == "New Chat":
                generated_title, is_auto = generate_conversation_title(
                    mode=mode,
                    first_message=message_text,
                    source_text=context.get("source_text") if isinstance(context, dict) else None,
                )
                conversation.title = generated_title
                conversation.is_title_auto = is_auto

            conversation.mode = mode
            conversation.last_message_at = timezone.now()
            conversation.save(update_fields=["title", "is_title_auto", "mode", "last_message_at", "updated_at"])

            try:
                answer_text, parsed_json, usage = call_assistant_model(
                    mode=mode,
                    message=message_text,
                    context=context,
                    history_messages=recent_history,
                )
            except Exception as exc:
                AssistantMessage.objects.create(
                    conversation=conversation,
                    role=AssistantMessage.ROLE_ASSISTANT,
                    content="",
                    status=AssistantMessage.STATUS_FAILED,
                    error_message=f"{type(exc).__name__}: {exc}",
                )
                release_quota(request.user, amount=1)
                return Response(
                    {
                        "detail": "AI service error",
                        "error": f"{type(exc).__name__}: {exc}",
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            assistant_content = json.dumps(parsed_json, ensure_ascii=False) if parsed_json is not None else json.dumps({"text": answer_text}, ensure_ascii=False)
            assistant_message = AssistantMessage.objects.create(
                conversation=conversation,
                role=AssistantMessage.ROLE_ASSISTANT,
                content=assistant_content,
                token_usage_prompt=usage.get("prompt_token_count"),
                token_usage_completion=usage.get("completion_token_count"),
                token_usage_total=usage.get("total_token_count"),
                status=AssistantMessage.STATUS_COMPLETED,
            )

        latest_quota = get_quota_status(request.user)

        return Response(
            {
                "message_id": user_message.id,
                "assistant_message_id": assistant_message.id,
                "answer": parsed_json if parsed_json is not None else answer_text,
                "mode": mode,
                "usage": usage,
                "quota": latest_quota,
            },
            status=status.HTTP_200_OK,
        )
