from ..authentication import CustomTokenAuthentication
from ..models import Teacher
from ..permissions import IsOwner
from ..serializers import TeacherSerializer, UserSerializer
from ..utils import get_absolute_media_url, validate_file_signature

from drf_spectacular.utils import (
    extend_schema, 
    OpenApiParameter, 
    OpenApiResponse,
    inline_serializer
)
from django.core.files.storage import default_storage

from rest_framework import generics, status, serializers
from rest_framework.response import Response


class TeacherRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsOwner]
    queryset = Teacher.objects.select_related("user").all()
    serializer_class = TeacherSerializer
    lookup_field = "pk"
    lookup_url_kwarg = "pk"

    @extend_schema(
        summary="Giáo viên - Xem hồ sơ cá nhân",
        description=(
            "Lấy thông tin hồ sơ giáo viên theo `pk` (pk = user_id/teacher_id).\n\n"
            "**Điều kiện:**\n"
            "- Người gọi phải đăng nhập\n"
            "- Tài khoản phải ở trạng thái `V` (Verified)\n"
            "- Chỉ được xem hồ sơ của chính mình (owner)\n\n"
            "**Response:** Trả về dữ liệu gộp từ User + Teacher, kèm `avatar_url`, `cover_url` và `credentials[].url` dạng absolute URL."
        ),
        tags=["teachers"],
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Teacher id (chính là user_id)",
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Teacher profile"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def get(self, request, *args, **kwargs):
        teacher = self.get_object()
        user = teacher.user
        user_data = UserSerializer(user).data
        teacher_data = TeacherSerializer(teacher).data

        user_data["avatar_url"] = get_absolute_media_url(user_data.get("avatar"))
        user_data["cover_url"] = get_absolute_media_url(user_data.get("cover"))
        user_data.pop("avatar", None)
        user_data.pop("cover", None)

        credentials = teacher_data.get("credentials", [])
        if isinstance(credentials, list):
            processed = []
            for item in credentials:
                if isinstance(item, dict) and item.get("url"):
                    item = item.copy()
                    item["url"] = get_absolute_media_url(item["url"])
                processed.append(item)
            teacher_data["credentials"] = processed

        return Response({**user_data, **teacher_data}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Giáo viên - Cập nhật hồ sơ cá nhân",
        description=(
            "Cập nhật hồ sơ giáo viên theo `pk` (pk = user_id/teacher_id).\n\n"
            "**Điều kiện:**\n"
            "- Người gọi phải đăng nhập\n"
            "- Tài khoản phải ở trạng thái `V` (Verified)\n"
            "- Chỉ được cập nhật hồ sơ của chính mình (owner)\n\n"
            "**FormData (multipart/form-data):**\n"
            "- User fields: `user.username`, `user.email`, `user.full_name`, `user.date_of_birth`, `user.avatar`(file), `user.cover`(file)\n"
            "- Teacher fields: `teacher.current_workplace`, `teacher.teacher_type`, `teacher.experience_year`, `teacher.introduction`\n"
            "- Credentials update (optional):\n"
            "  - `teacher.credentials_state`: JSON string list các item `{id, choice}` với choice ∈ {unchange, remove, replace, upload}\n"
            "  - File theo id: `credentials_<id>` (ví dụ replace/upload id=2 thì gửi file key `credentials_2`)\n\n"
            "**Lưu ý credentials:**\n"
            "- `unchange/remove/replace` yêu cầu id phải tồn tại trong DB\n"
            "- `upload` yêu cầu id chưa tồn tại\n"
            "- `remove/replace` sẽ delete object cũ trên GCS\n"
            "- `replace/upload` sẽ validate file (size<=5MB, mime/pdf|jpeg|png, magic number) rồi upload lên GCS"
        ),
        tags=["teachers"],
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Teacher id (chính là user_id)",
                required=True,
            ),
        ],
        request=inline_serializer(
            name="TeacherUpdateProfileRequest",
            fields={
                "user.username": serializers.CharField(required=False),
                "user.email": serializers.EmailField(required=False),
                "user.full_name": serializers.CharField(required=False),
                "user.date_of_birth": serializers.DateField(required=False),
                "user.avatar": serializers.FileField(required=False),
                "user.cover": serializers.FileField(required=False),
                "teacher.current_workplace": serializers.CharField(required=False),
                "teacher.teacher_type": serializers.ChoiceField(choices=["S", "C", "F"], required=False),
                "teacher.experience_year": serializers.IntegerField(required=False),
                "teacher.introduction": serializers.CharField(required=False),
                "teacher.credentials_state": serializers.CharField(required=False, help_text="JSON string"),
                "credentials_0": serializers.FileField(required=False),
                "credentials_1": serializers.FileField(required=False),
                "credentials_2": serializers.FileField(required=False),
                "credentials_3": serializers.FileField(required=False),
            },
        ),
        responses={
            200: OpenApiResponse(description="Teacher profile updated"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden"),
            404: OpenApiResponse(description="Not found"),
        },
    )
    def patch(self, request, *args, **kwargs):
        teacher = self.get_object()
        user = teacher.user

        # --- update User fields (partial) ---
        user_update_fields = {}
        user_fields = ["username", "email", "full_name", "date_of_birth"]
        for field in user_fields:
            key = f"user.{field}"
            if key in request.data:
                user_update_fields[field] = request.data.get(key)

        avatar_file = request.FILES.get("user.avatar")
        if avatar_file is not None:
            user_update_fields["avatar"] = avatar_file

        cover_file = request.FILES.get("user.cover")
        if cover_file is not None:
            user_update_fields["cover"] = cover_file

        user_serializer = UserSerializer(user, data=user_update_fields, partial=True)
        user_serializer.is_valid(raise_exception=True)

        # --- update Teacher fields (partial) ---
        teacher_update_fields = {}
        teacher_fields = [
            "current_workplace",
            "teacher_type",
            "experience_year",
            "introduction",
        ]
        for field in teacher_fields:
            key = f"teacher.{field}"
            if key in request.data:
                teacher_update_fields[field] = request.data.get(key)

        # --- credentials_state patch (optional) ---
        credentials_state_raw = request.data.get("teacher.credentials_state")

        if credentials_state_raw is not None:
            import json

            try:
                credentials_state = json.loads(credentials_state_raw)
            except Exception:
                return Response(
                    {"teacher.credentials_state": "Invalid JSON"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not isinstance(credentials_state, list):
                return Response(
                    {"teacher.credentials_state": "Must be a list"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            existing = teacher.credentials if isinstance(teacher.credentials, list) else []
            existing_by_id = {}
            for item in existing:
                if isinstance(item, dict) and isinstance(item.get("id"), int):
                    existing_by_id[item["id"]] = item

            new_credentials = []

            def _validate_and_detect_type(uploaded_file):
                if not uploaded_file:
                    raise ValueError("Missing file")

                if uploaded_file.size > 5 * 1024 * 1024:
                    raise ValueError(
                        f"Credential file '{uploaded_file.name}' exceeds 5MB limit"
                    )

                valid_content_types = ["application/pdf", "image/jpeg", "image/png"]
                if uploaded_file.content_type not in valid_content_types:
                    raise ValueError(
                        f"Credential file '{uploaded_file.name}' has invalid content type: {uploaded_file.content_type}"
                    )

                file_type = validate_file_signature(uploaded_file)
                if file_type not in ["pdf", "jpeg", "png"]:
                    raise ValueError(
                        f"Credential file '{uploaded_file.name}' has invalid file signature"
                    )

                return file_type

            extension_map = {"pdf": ".pdf", "jpeg": ".jpg", "png": ".png"}

            for entry in credentials_state:
                if not isinstance(entry, dict):
                    return Response(
                        {"teacher.credentials_state": "Each item must be an object"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                cred_id = entry.get("id")
                choice = entry.get("choice")

                if not isinstance(cred_id, int):
                    return Response(
                        {"teacher.credentials_state": "Each item must have integer id"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if choice not in ["unchange", "remove", "replace", "upload"]:
                    return Response(
                        {"teacher.credentials_state": f"Invalid choice for id={cred_id}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                exists = cred_id in existing_by_id

                if choice in ["unchange", "remove", "replace"] and not exists:
                    return Response(
                        {"teacher.credentials_state": f"Credential id={cred_id} does not exist"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if choice == "upload" and exists:
                    return Response(
                        {"teacher.credentials_state": f"Credential id={cred_id} already exists"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if choice == "unchange":
                    new_credentials.append(existing_by_id[cred_id])
                    continue

                if choice == "remove":
                    old = existing_by_id[cred_id]
                    old_url = old.get("url") if isinstance(old, dict) else None
                    if old_url:
                        default_storage.delete(old_url)
                    continue

                if choice in ["replace", "upload"]:
                    file_key = f"credentials_{cred_id}"
                    uploaded_file = request.FILES.get(file_key)
                    if not uploaded_file:
                        return Response(
                            {file_key: "File is required"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    try:
                        file_type = _validate_and_detect_type(uploaded_file)
                    except ValueError as e:
                        return Response(
                            {file_key: str(e)},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    if choice == "replace":
                        old = existing_by_id[cred_id]
                        old_url = old.get("url") if isinstance(old, dict) else None
                        if old_url:
                            default_storage.delete(old_url)

                    filename = f"cert_{cred_id}{extension_map[file_type]}"
                    storage_path = f"teachers/credentials/{user.file_storage_uuid}/{filename}"
                    saved_path = default_storage.save(storage_path, uploaded_file)

                    new_item = {
                        "id": cred_id,
                        "url": saved_path,
                        "name": uploaded_file.name,
                        "type": uploaded_file.content_type,
                        "size": uploaded_file.size,
                    }

                    new_credentials.append(new_item)

            if len(new_credentials) == 0 or len(new_credentials) > 3:
                return Response(
                    {
                        "credentials": "At least one credential is required and maximum 3 credentials are allowed."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            teacher_update_fields["credentials"] = new_credentials

        teacher_serializer = TeacherSerializer(
            teacher, data=teacher_update_fields, partial=True, context={"user": user}
        )
        teacher_serializer.is_valid(raise_exception=True)

        user_serializer.save()
        teacher_serializer.save()

        user_data = UserSerializer(user).data
        teacher_data = TeacherSerializer(teacher).data

        user_data["avatar_url"] = get_absolute_media_url(user_data.get("avatar"))
        user_data["cover_url"] = get_absolute_media_url(user_data.get("cover"))
        user_data.pop("avatar", None)
        user_data.pop("cover", None)

        credentials = teacher_data.get("credentials", [])
        if isinstance(credentials, list):
            processed = []
            for item in credentials:
                if isinstance(item, dict) and item.get("url"):
                    item = item.copy()
                    item["url"] = get_absolute_media_url(item["url"])
                processed.append(item)
            teacher_data["credentials"] = processed

        return Response(
            {
                "message": "Teacher profile updated successfully",
                "data": {**user_data, **teacher_data},
            },
            status=status.HTTP_200_OK,
        )
