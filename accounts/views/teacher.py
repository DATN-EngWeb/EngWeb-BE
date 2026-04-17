from django.conf import settings
from ..authentication import CustomTokenAuthentication
from ..models import Teacher
from ..permissions import IsOwner
from ..serializers import TeacherSerializer, UserSerializer
from ..utils import get_absolute_media_url, validate_file_signature

from drf_spectacular.utils import (
    extend_schema, 
    OpenApiParameter, 
    OpenApiResponse,
    OpenApiExample,
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
    http_method_names = ["get", "patch"]

    @extend_schema(
        summary="Teacher - View personal profile",
        description=(
            "Get teacher personal profile by `pk` (pk = user_id/teacher_id).\n\n"
            "**Conditions:**\n"
            "- Must be logged in\n"
            "- User must be in status `V` (Verified)\n"
            "- Only owner can view their own profile\n\n"
            "**Response:** Data from User + Teacher, including `avatar_url`, `cover_url` and `credentials[].url` as absolute URL."
        ),
        tags=["teacher"],
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Teacher id (same as user_id)",
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Teacher profile data",
                response=inline_serializer(
                    name="TeacherProfileGetResponse",
                    fields={
                        "id": serializers.IntegerField(),
                        "last_login": serializers.DateTimeField(allow_null=True),
                        "username": serializers.CharField(),
                        "is_active": serializers.BooleanField(),
                        "date_joined": serializers.DateTimeField(),
                        "email": serializers.EmailField(),
                        "file_storage_uuid": serializers.UUIDField(),
                        "full_name": serializers.CharField(allow_null=True),
                        "date_of_birth": serializers.DateField(allow_null=True),
                        "status": serializers.CharField(),
                        "role": serializers.CharField(),
                        "updated_at": serializers.DateTimeField(),
                        "avatar_url": serializers.URLField(allow_null=True),
                        "cover_url": serializers.URLField(allow_null=True),
                        "user": serializers.IntegerField(),
                        "current_workplace": serializers.CharField(),
                        "teacher_type": serializers.CharField(),
                        "experience_year": serializers.IntegerField(),
                        "introduction": serializers.CharField(),
                        "credentials": serializers.ListField(child=serializers.DictField()),
                        "created_at": serializers.DateTimeField(),
                    }
                ),
                examples=[
                    OpenApiExample(
                        name="Teacher profile response",
                        value={
                            "id": 4,
                            "last_login": "2026-01-25T16:56:37.311391+07:00",
                            "username": "teacher",
                            "is_active": True,
                            "date_joined": "2026-01-25T16:54:00.499454+07:00",
                            "email": "vulopd7cbl@gmail.com",
                            "file_storage_uuid": "6ca84bec-0519-4b5b-a3ba-a96d48c3b6bc",
                            "full_name": "Nguyễn Hoàng Vũ",
                            "date_of_birth": "2004-09-03",
                            "status": "V",
                            "role": "T",
                            "updated_at": "2026-01-25T16:55:15.617290+07:00",
                            "avatar_url": f"{settings.MEDIA_URL.rstrip('/')}/users/avatars/teacher-avatar.jpg?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=dev-nens-english-app-sa%40dev-nens-english-app.iam.gserviceaccount.com%2F20260125%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20260125T095705Z&X-Goog-Expires=86400&X-Goog-SignedHeaders=host&X-Goog-Signature=d1b2787d936a5589d64054e81fb63feec8037d320088a3c31f472a43ee6b61edfcffe60254657ec7be8d8bd6687505d94749cbb9c9e9a86a3eaf2d77c66c481c75e9d513dda0ca5230e947076f9f7e9a7e8ff82e864c47bf6412998f5ab287af5020fd78858643176015e07b198bb917d690f672260ad78a63bf4d59e09305c5717b4558a65239b552102c5f15eea02aa48e10f7ad43df143700cd73bd9aeb846f8a562fc5dfba3c867c39d41e3f46e8993dddd912e78e641fd2658c51a529b87713fceb08a8b14af0eee0b3f7a8b4d89a746945676d01e96bf335dc5ddee88b0263e788de1b69c9a6f2a3fca2672be78c17a97f29d9fac52861936908e4912c",
                            "cover_url": f"{settings.MEDIA_URL.rstrip('/')}/users/covers/default-cover.jpg?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=dev-nens-english-app-sa%40dev-nens-english-app.iam.gserviceaccount.com%2F20260125%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20260125T095705Z&X-Goog-Expires=86400&X-Goog-SignedHeaders=host&X-Goog-Signature=6cefa4a8076e971b170bee3628b49e5dbb4f373d2417cd3aa5aba8ea38db658eb6dfa6d4c7c6fda7ee9592d4f82a52c10b5a99f009da45278578c380aabf39358ed1d59ab69c2a86218a44ad8c3dbb1cd8a4d103421b88b2e59fa16a904ae57448e552ac71e859bf6c5534da98405c9bba3b93338fd7b439fbb0cdcacb41225256c06f48b5b14be647fad157ff59430be017022905d4f82adb33c6f7eb40d653930d4ed7b5198b8964a025ef21126596d46311a877854c4a7427bdefd3f974ff7ca26a9888b7a259d437bf2f80a0075f130b70db0d04f9754455c81a0f317b5e3ec09e4fa2ec10193823096fd56587919577be4d1d72d9cb3e5518939afd8ef2",
                            "user": 4,
                            "current_workplace": "Pizza 4P's",
                            "teacher_type": "C",
                            "experience_year": 1,
                            "introduction": "I am a Data Engineer.",
                            "credentials": [
                                {
                                    "id": 0,
                                    "url": f"{settings.MEDIA_URL.rstrip('/')}/teachers/credentials/6ca84bec-0519-4b5b-a3ba-a96d48c3b6bc/credential_0.jpg",
                                    "name": "credential_0.jpg",
                                    "size": 63341,
                                    "type": "image/jpeg"
                                },
                                {
                                    "id": 1,
                                    "url": f"{settings.MEDIA_URL.rstrip('/')}/teachers/credentials/6ca84bec-0519-4b5b-a3ba-a96d48c3b6bc/credential_1.jpg",
                                    "name": "credential_1.jpg",
                                    "size": 8096,
                                    "type": "image/jpeg"
                                }
                            ],
                            "created_at": "2026-01-25T16:55:15.617279+07:00",
                        },
                    ),
                ],
            )
        }
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
        summary="Teacher - Update personal profile",
        description=(
            "Update teacher personal profile by `pk` (pk = user_id/teacher_id).\n\n"
            "**Conditions:**\n"
            "- Must be logged in\n"
            "- User must be in status `V` (Verified)\n"
            "- Only owner can update their own profile\n\n"
            "**FormData (multipart/form-data):**\n"
            "- User fields: `user.username`, `user.email`, `user.full_name`, `user.date_of_birth`, `user.avatar`(file), `user.cover`(file)\n"
            "- Teacher fields: `teacher.current_workplace`, `teacher.teacher_type`, `teacher.experience_year`, `teacher.introduction`\n"
            "- Credentials update (optional):\n"
            "  - `teacher.credentials_state`: JSON string list of items `{id, choice}` with choice ∈ {unchange, remove, replace, upload}\n"
            "  - File by id: `credentials_<id>` (e.g. replace/upload id=2 then send file key `credentials_2`)\n\n"
            "**Note on credentials:**\n"
            "- `unchange/remove/replace` requires id to exist in DB\n"
            "- `upload` requires id to not exist\n"
            "- `remove/replace` will delete old object on GCS\n"
            "- `replace/upload` will validate file (size<=5MB, mime/pdf|jpeg|png, magic number) and upload to GCS"
        ),
        tags=["teacher"],
        parameters=[
            OpenApiParameter(
                name="pk",
                type=int,
                location=OpenApiParameter.PATH,
                description="Teacher id (same as user_id)",
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
                "credentials_0": serializers.FileField(required=False), # test replace
                "credentials_1": serializers.FileField(required=False), # test unchange
                "credentials_2": serializers.FileField(required=False), # test remove
                "credentials_3": serializers.FileField(required=False), # test upload
            },
        ),
        responses={
            200: OpenApiResponse(
                description="Teacher profile updated successfully",
                response={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "data": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "last_login": {"type": "string", "format": "date-time", "nullable": True},
                                "username": {"type": "string"},
                                "is_active": {"type": "boolean"},
                                "date_joined": {"type": "string", "format": "date-time"},
                                "email": {"type": "string"},
                                "file_storage_uuid": {"type": "string", "format": "uuid"},
                                "full_name": {"type": "string", "nullable": True},
                                "date_of_birth": {"type": "string", "format": "date", "nullable": True},
                                "status": {"type": "string"},
                                "role": {"type": "string"},
                                "updated_at": {"type": "string", "format": "date-time"},
                                "avatar_url": {"type": "string", "format": "uri", "nullable": True},
                                "cover_url": {"type": "string", "format": "uri", "nullable": True},
                                "user": {"type": "integer"},
                                "current_workplace": {"type": "string"},
                                "teacher_type": {"type": "string"},
                                "experience_year": {"type": "integer"},
                                "introduction": {"type": "string"},
                                "credentials": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "url": {"type": "string", "format": "uri"},
                                            "name": {"type": "string"},
                                            "type": {"type": "string"},
                                            "size": {"type": "integer"},
                                        },
                                    },
                                },
                                "created_at": {"type": "string", "format": "date-time"},
                            },
                        },
                    },
                },
                examples=[
                    OpenApiExample(
                        name="Teacher profile update response",
                        value={
                            "message": "Teacher profile updated successfully",
                            "data": {
                                "id": 3,
                                "last_login": "2026-01-25T17:28:47.027817+07:00",
                                "username": "test_teacher_update",
                                "is_active": True,
                                "date_joined": "2026-01-25T17:26:11.879805+07:00",
                                "email": "teacherhehe@gmail.com",
                                "file_storage_uuid": "750aea4f-817e-4a14-b57b-49ad6983195b",
                                "full_name": "tha em",
                                "date_of_birth": "2004-05-01",
                                "status": "V",
                                "role": "T",
                                "updated_at": "2026-01-25T17:29:11.088658+07:00",
                                "avatar_url": f"{settings.MEDIA_URL.rstrip('/')}/users/avatars/test_teacher_avatar.png?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=dev-nens-english-app-sa%40dev-nens-english-app.iam.gserviceaccount.com%2F20260125%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20260125T102911Z&X-Goog-Expires=86400&X-Goog-SignedHeaders=host&X-Goog-Signature=5ad3d926437ae88164d2a48c4e6049803c7e4ef8714d8dd1331626a6705d874448e0d95a7ee77cc719503374e9276a804a89a694fee1537e8eb3554a8bc5c903cb3bc066cf097d0c24870b96951371052dd67e28ad459a33d586579b79261f2b27b8e0a78afb743acd552d9d96c1f4dad91a2056c07936aef9125358b33b831a7ce01019bca7e8bb57da506d6cf1caa7c40c73c2b2d34e969cb9182132fe093dc36eacae50e4688665717a822d949e615c0e2e2e305ca5f508354cbca0f44f5f1a3ff7cfe21e2619405a9d0fc3bddd4b99426d172a0674d677c392cda27d4d0150b54e225146b380cd502014f08f0397740044663b904a17f59e721ba0a2237a",
                                "cover_url": f"{settings.MEDIA_URL.rstrip('/')}/users/covers/teacher_cover_test.png?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=dev-nens-english-app-sa%40dev-nens-english-app.iam.gserviceaccount.com%2F20260125%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20260125T102911Z&X-Goog-Expires=86400&X-Goog-SignedHeaders=host&X-Goog-Signature=07f774e058a42697ed784fcbff1975896147944c3ab918dafdd2ed996c990693ee63712e13109a4c4f4c46a5c148a42c8687d2535b2114cba2d8a6bdbce0ec59713135c418d2508d31a17f1cc4a012f833361d5690676d87429c2faa133954d284f288adf532203cb1334c3d2df258395992563aa151a987a68f33d52b2c74856c27b520a5812d4dea547d976589b35eec41326c683f0d728e6e35ba7ba534fa7a94868de829a6abe933afd73b98100c4e2c73008b988460034b8cfb10801ec742dc635b4070e60d48ef79d8aaac3aa81649d86afb1c7b17e1b5af98a865f31292d0a66c3d263d6c829d9d45b79bbdf5d8ade0fd175895c7e35ef9c6e41e4b8f",
                                "user": 3,
                                "current_workplace": "ttt",
                                "teacher_type": "F",
                                "experience_year": 8,
                                "introduction": "Thua",
                                "credentials": [
                                    {
                                        "id": 0,
                                        "url": f"{settings.MEDIA_URL.rstrip('/')}/teachers/credentials/750aea4f-817e-4a14-b57b-49ad6983195b/credential_0.jpg",
                                        "name": "credential_0.jpg",
                                        "type": "image/jpeg",
                                        "size": 11488
                                    },
                                    {
                                        "id": 1,
                                        "url": f"{settings.MEDIA_URL.rstrip('/')}/teachers/credentials/750aea4f-817e-4a14-b57b-49ad6983195b/credential_1.jpg",
                                        "name": "credential_1.jpg",
                                        "size": 8096,
                                        "type": "image/jpeg"
                                    },
                                    {
                                        "id": 3,
                                        "url": f"{settings.MEDIA_URL.rstrip('/')}/teachers/credentials/750aea4f-817e-4a14-b57b-49ad6983195b/credential_3.jpg",
                                        "name": "credential_3.jpg",
                                        "type": "image/jpeg",
                                        "size": 7479
                                    }
                                ],
                                "created_at": "2026-01-25T17:26:42.804724+07:00",
                            },
                        },
                    ),
                ],
            ),
        },
    )
    def patch(self, request, *args, **kwargs):
        teacher = self.get_object()
        user = teacher.user
        user_update_fields = {}
        user_fields = ["username", "email", "full_name", "date_of_birth"]
        
        for field in user_fields:
            key = f"user.{field}"
            
            if key in request.data:
                user_update_fields[field] = request.data.get(key)

        avatar_file = request.FILES.get("user.avatar")
        
        if avatar_file is not None:
            # Delete old avatar if it's not the default one
            old_avatar = user.avatar
            if old_avatar and str(old_avatar) != "users/avatars/default-avatar.jpg":
                try:
                    default_storage.delete(str(old_avatar))
                except Exception:
                    pass  # Ignore errors when deleting old file
            user_update_fields["avatar"] = avatar_file

        cover_file = request.FILES.get("user.cover")
        
        if cover_file is not None:
            # Delete old cover if it's not the default one
            old_cover = user.cover
            if old_cover and str(old_cover) != "users/covers/default-cover.jpg":
                try:
                    default_storage.delete(str(old_cover))
                except Exception:
                    pass  # Ignore errors when deleting old file
            user_update_fields["cover"] = cover_file

        user_serializer = UserSerializer(user, data=user_update_fields, partial=True)
        user_serializer.is_valid(raise_exception=True)
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
                    raise ValueError(f"Credential file '{uploaded_file.name}' exceeds 5MB limit")

                valid_content_types = ["application/pdf", "image/jpeg", "image/png"]

                if uploaded_file.content_type not in valid_content_types:
                    raise ValueError(f"Credential file '{uploaded_file.name}' has invalid content type: {uploaded_file.content_type}")

                file_type = validate_file_signature(uploaded_file)
                if file_type not in ["pdf", "jpeg", "png"]:
                    raise ValueError(f"Credential file '{uploaded_file.name}' has invalid file signature")

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

                    filename = f"credential_{cred_id}{extension_map[file_type]}"
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
                "data": {**user_data, **teacher_data}
            },
            status=status.HTTP_200_OK
        )
