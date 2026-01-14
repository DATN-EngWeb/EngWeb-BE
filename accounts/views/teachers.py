from rest_framework import generics, status, serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter, inline_serializer

from ..models import User, Teacher
from ..serializers import UserSerializer, TeacherSerializer
from ..permissions import IsOwner
from ..authentication import CustomTokenAuthentication
from ..utils import (
    get_absolute_media_url,
    get_s3_key_from_imagefield,
    get_s3_key_from_credential_url,
    delete_old_file_from_s3,
    process_credential_files,
)


class TeacherRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Teacher Retrieve, Update, Destroy API
    
    - GET: Retrieve teacher profile (Owner only, status must be 'V')
    - PATCH: Update teacher profile (Owner only)
    - DELETE: Not implemented (use User endpoint for account management)
    """
    permission_classes = [IsOwner]
    authentication_classes = [CustomTokenAuthentication]
    queryset = User.objects.filter(role='T')
    serializer_class = UserSerializer
    lookup_field = 'pk'
    lookup_url_kwarg = 'pk'
    # Allow only GET and PATCH
    http_method_names = ['get', 'patch']

    def get_serializer_context(self):
        """Add request to serializer context for building absolute URLs"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @extend_schema(
        operation_id="teacher_retrieve",
        summary="Xem thông tin giáo viên",
        description=(
            "Lấy thông tin chi tiết profile của giáo viên.\n\n"
            "**Yêu cầu:**\n"
            "- Phải là chủ sở hữu (owner) của tài khoản\n"
            "- Tài khoản phải ở trạng thái 'V' (Verified)\n\n"
            "**Response bao gồm:**\n"
            "- Thông tin User (full_name, date_of_birth, email, avatar_url, cover_url)\n"
            "- Thông tin Teacher (current_workplace, teacher_type, experience_year, introduction)\n"
            "- Credentials với absolute URLs cho certificates"
        ),
        tags=["teachers"],
        parameters=[
            OpenApiParameter(
                name='pk',
                type=int,
                location=OpenApiParameter.PATH,
                description='ID của teacher (user_id)',
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Thông tin chi tiết của teacher",
                response={
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "example": 123},
                        "username": {"type": "string", "example": "teacherx"},
                        "email": {"type": "string", "example": "sarah.w@example.com"},
                        "full_name": {"type": "string", "example": "Sarah Wilson"},
                        "date_of_birth": {"type": "string", "format": "date", "example": "1990-01-01"},
                        "role": {"type": "string", "enum": ["T"], "example": "T"},
                        "role_display": {"type": "string", "example": "Teacher"},
                        "status": {"type": "string", "enum": ["V"], "example": "V"},
                        "status_display": {"type": "string", "example": "Verified"},
                        "avatar_url": {
                            "type": "string",
                            "nullable": True,
                            "example": "http://localhost:9000/englishapp/media/users/avatars/{uuid}/avatar.jpg"
                        },
                        "cover_url": {
                            "type": "string",
                            "nullable": True,
                            "example": "http://localhost:9000/englishapp/media/users/covers/{uuid}/cover.jpg"
                        },
                        "current_workplace": {"type": "string", "example": "Ho Chi Minh city"},
                        "teacher_type": {"type": "string", "enum": ["S", "C", "F"], "example": "F"},
                        "teacher_type_display": {"type": "string", "example": "Freelance"},
                        "experience_year": {"type": "integer", "example": 2},
                        "introduction": {"type": "string", "example": "Professional teacher with many students"},
                        "credentials": {
                            "type": "object",
                            "properties": {
                                "certificates": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "url": {"type": "string"},
                                            "name": {"type": "string"},
                                            "type": {"type": "string"},
                                            "size": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        },
                        "date_joined": {"type": "string", "format": "date-time"},
                        "last_login": {"type": "string", "format": "date-time", "nullable": True},
                        "created_at": {"type": "string", "format": "date-time"},
                        "updated_at": {"type": "string", "format": "date-time"},
                    }
                },
            ),
            400: OpenApiResponse(
                description="Tài khoản chưa được xác thực (status khác 'V')",
            ),
            403: OpenApiResponse(
                description="Không có quyền truy cập (không phải owner)",
            ),
            404: OpenApiResponse(
                description="Không tìm thấy teacher",
            ),
        },
    )
    def get(self, request, pk=None):
        """
        Retrieve teacher profile
        - Check if user is owner
        - Check if status is 'V' (Verified)
        - Return user + teacher data with absolute URLs
        """
        try:
            user = self.get_object()
        except User.DoesNotExist:
            return Response(
                {"error": "Teacher not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if user is teacher
        if user.role != 'T':
            return Response(
                {"error": "User is not a teacher"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check status - must be 'V' (Verified)
        if user.status != 'V':
            return Response(
                {
                    "error": "User needs to be verified.",
                    "status": user.status,
                    "status_display": user.get_status_display(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get user data
        user_serializer = UserSerializer(user, context={'request': request})
        user_data = user_serializer.data

        # Get teacher data
        try:
            teacher = user.teacher
            teacher_serializer = TeacherSerializer(teacher, context={'request': request})
            teacher_data = teacher_serializer.data

            # Process credentials to absolute URLs
            credentials = teacher_data.get('credentials', {})
            if credentials and 'certificates' in credentials:
                certificates = credentials['certificates']
                processed_certificates = []
                for cert in certificates:
                    cert_url = cert.get('url', '')
                    if cert_url:
                        absolute_url = get_absolute_media_url(cert_url, request)
                        processed_cert = cert.copy()
                        processed_cert['url'] = absolute_url
                        processed_certificates.append(processed_cert)
                    else:
                        processed_certificates.append(cert)
                credentials['certificates'] = processed_certificates
                teacher_data['credentials'] = credentials

            # Merge teacher data into user data
            user_data.update(teacher_data)
            user_data['teacher_type_display'] = teacher.get_teacher_type_display()
        except Teacher.DoesNotExist:
            return Response(
                {"error": "Teacher profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Add display fields
        user_data['role_display'] = user.get_role_display()
        user_data['status_display'] = user.get_status_display()

        # Convert avatar to avatar_url
        avatar = user_data.get('avatar')
        user_data['avatar_url'] = get_absolute_media_url(avatar, request)
        user_data.pop('avatar', None)

        # Convert cover to cover_url
        cover = user_data.get('cover')
        user_data['cover_url'] = get_absolute_media_url(cover, request)
        user_data.pop('cover', None)

        return Response(user_data, status=status.HTTP_200_OK)


    @extend_schema(
        operation_id="teacher_update",
        summary="Cập nhật thông tin giáo viên",
        description=(
            "Cập nhật profile của giáo viên (partial update - chỉ cập nhật các fields được gửi).\n\n"
            "**Yêu cầu:**\n"
            "- Phải là chủ sở hữu (owner) của tài khoản\n"
            "- Tài khoản phải ở trạng thái 'V' (Verified)\n\n"
            "**Format:** Multipart Form-Data\n\n"
            "**User fields (optional):**\n"
            "- `user.full_name`: Họ và tên (string)\n"
            "- `user.date_of_birth`: Ngày sinh (YYYY-MM-DD)\n"
            "- `user.avatar`: Ảnh đại diện (image file - JPEG, PNG)\n"
            "- `user.cover`: Ảnh bìa (image file - JPEG, PNG)\n"
            "- `old_password`: Mật khẩu cũ (string, required nếu muốn đổi mật khẩu)\n"
            "- `new_password`: Mật khẩu mới (string, required nếu muốn đổi mật khẩu, tối thiểu 8 ký tự)\n\n"
            "**Teacher fields (optional):**\n"
            "- `current_workplace`: Nơi làm việc (string)\n"
            "- `teacher_type`: Loại giáo viên - S (School), C (Center), F (Freelance)\n"
            "- `experience_year`: Năm kinh nghiệm (integer)\n"
            "- `introduction`: Giới thiệu (string)\n\n"
            "**Credentials (optional):**\n"
            "- `credentials`: Chứng chỉ/bằng cấp (multiple files - PDF, JPEG, PNG)\n"
            "- Nếu gửi credentials files, sẽ **replace** toàn bộ credentials hiện tại\n\n"
            "**Lưu ý:**\n"
            "- File cũ (avatar, cover, credentials) sẽ tự động bị xóa khỏi MinIO sau khi update thành công\n"
            "- Để đổi mật khẩu: phải gửi cả `old_password` và `new_password`\n"
            "- Mật khẩu mới phải khác mật khẩu cũ và tối thiểu 8 ký tự\n"
            "- Chỉ cần gửi các fields muốn update, không cần gửi tất cả"
        ),
        tags=["teachers"],
        parameters=[
            OpenApiParameter(
                name='pk',
                type=int,
                location=OpenApiParameter.PATH,
                description='ID của teacher (user_id)',
                required=True,
            ),
        ],
        request=inline_serializer(
            name="TeacherUpdateRequest",
            fields={
                "user.full_name": serializers.CharField(required=False),
                "user.date_of_birth": serializers.DateField(required=False),
                "user.avatar": serializers.ImageField(required=False),
                "user.cover": serializers.ImageField(required=False),
                "old_password": serializers.CharField(required=False, write_only=True, help_text="Mật khẩu cũ (required nếu muốn đổi mật khẩu)"),
                "new_password": serializers.CharField(required=False, write_only=True, help_text="Mật khẩu mới (required nếu muốn đổi mật khẩu, tối thiểu 8 ký tự)"),
                "current_workplace": serializers.CharField(required=False),
                "teacher_type": serializers.ChoiceField(choices=["S", "C", "F"], required=False),
                "experience_year": serializers.IntegerField(required=False),
                "introduction": serializers.CharField(required=False),
                "credentials": serializers.ListField(
                    child=serializers.FileField(), required=False
                ),
            },
        ),
        responses={
            200: OpenApiResponse(
                description="Teacher profile updated successfully",
                response={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "example": "Teacher profile updated successfully"},
                        "data": {
                            "type": "object",
                            "description": "Updated teacher profile data (same structure as GET response)"
                        }
                    }
                },
            ),
            400: OpenApiResponse(
                description="Validation error or account not verified",
            ),
            403: OpenApiResponse(
                description="Không có quyền truy cập (không phải owner)",
            ),
            404: OpenApiResponse(
                description="Không tìm thấy teacher",
            ),
        },
    )
    def patch(self, request, pk=None):
        """
        Update teacher profile (partial update)
        - Check if user is owner
        - Check if status is 'V' (Verified)
        - Update only provided fields
        - Delete old files from S3 after successful update
        """
        try:
            user = self.get_object()
        except User.DoesNotExist:
            return Response(
                {"error": "Teacher not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if user is teacher
        if user.role != 'T':
            return Response(
                {"error": "User is not a teacher"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check status - must be 'V' (Verified)
        if user.status != 'V':
            return Response(
                {
                    "error": "Account needs to be verified.",
                    "status": user.status,
                    "status_display": user.get_status_display(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get teacher
        try:
            teacher = user.teacher
        except Teacher.DoesNotExist:
            return Response(
                {"error": "Teacher profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Save old S3 keys before update (for deletion after successful update)
        old_avatar_key = get_s3_key_from_imagefield(user.avatar) if user.avatar else None
        old_cover_key = get_s3_key_from_imagefield(user.cover) if user.cover else None
        
        # Save old credentials certificates before update (for deletion after successful update)
        old_credentials = teacher.credentials if hasattr(teacher, 'credentials') and teacher.credentials else {}
        old_certificates = old_credentials.get('certificates', []) if isinstance(old_credentials, dict) else []

        # Track if avatar/cover/credentials are being updated
        avatar_updated = False
        cover_updated = False
        credentials_updated = False

        # Update User fields (partial update)
        user_errors = {}
        password_updated = False
        
        if "user.full_name" in request.data:
            full_name = request.data.get("user.full_name", "").strip()
            if full_name:
                user.full_name = full_name
            else:
                user_errors["full_name"] = "This field cannot be empty."
        
        if "user.date_of_birth" in request.data:
            date_of_birth = request.data.get("user.date_of_birth")
            if date_of_birth:
                user.date_of_birth = date_of_birth
            else:
                user_errors["date_of_birth"] = "This field cannot be empty."

        if "user.avatar" in request.FILES:
            avatar_file = request.FILES.get("user.avatar")
            if avatar_file:
                user.avatar = avatar_file
                avatar_updated = True

        if "user.cover" in request.FILES:
            cover_file = request.FILES.get("user.cover")
            if cover_file:
                user.cover = cover_file
                cover_updated = True

        # Handle password change
        if "old_password" in request.data or "new_password" in request.data:
            old_password = request.data.get("old_password")
            new_password = request.data.get("new_password")
            
            # Both fields are required for password change
            if not old_password or not new_password:
                user_errors["password"] = "Both old_password and new_password are required to change password."
            else:
                # Verify old password
                if not user.check_password(old_password):
                    user_errors["old_password"] = "Old password is incorrect."
                else:
                    # Validate new password strength
                    if len(new_password) < 8:
                        user_errors["new_password"] = "Password must be at least 8 characters long."
                    elif new_password == old_password:
                        user_errors["new_password"] = "New password must be different from old password."
                    else:
                        # Set new password
                        user.set_password(new_password)
                        password_updated = True

        if user_errors:
            return Response({"user": user_errors}, status=status.HTTP_400_BAD_REQUEST)

        # Update Teacher fields (partial update)
        teacher_data = {}
        
        if "current_workplace" in request.data:
            current_workplace = request.data.get("current_workplace", "").strip()
            if current_workplace:
                teacher_data["current_workplace"] = current_workplace
        
        if "teacher_type" in request.data:
            teacher_type = request.data.get("teacher_type")
            if teacher_type in ['S', 'C', 'F']:
                teacher_data["teacher_type"] = teacher_type
        
        if "experience_year" in request.data:
            experience_year = request.data.get("experience_year")
            if experience_year is not None:
                try:
                    teacher_data["experience_year"] = int(experience_year)
                except (ValueError, TypeError):
                    return Response(
                        {"experience_year": "Must be a valid integer."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        
        if "introduction" in request.data:
            introduction = request.data.get("introduction", "").strip()
            if introduction:
                teacher_data["introduction"] = introduction

        # Handle credentials (replace if provided)
        if "credentials" in request.FILES:
            credential_files = request.FILES.getlist("credentials")
            if credential_files:
                # Process new credential files
                credentials_data = process_credential_files(request.FILES, user)
                
                # Validate at least one certificate
                if not credentials_data.get("certificates") or len(credentials_data.get("certificates", [])) == 0:
                    return Response(
                        {"credentials": "At least one certificate is required."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                
                teacher_data["credentials"] = credentials_data
                credentials_updated = True

        # Validate teacher data if any teacher fields are being updated
        if teacher_data:
            # Use serializer to validate
            teacher_serializer = TeacherSerializer(teacher, data=teacher_data, partial=True)
            if not teacher_serializer.is_valid():
                return Response(teacher_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Update teacher fields
            for attr, value in teacher_data.items():
                setattr(teacher, attr, value)
            teacher.save()

        # Save user if any user fields were updated
        if any([
            "user.full_name" in request.data,
            "user.date_of_birth" in request.data,
            avatar_updated,
            cover_updated,
            password_updated
        ]):
            user.save()

        # Delete old files from S3 after successful update
        # Only delete if file was actually updated (new file uploaded)
        if avatar_updated and old_avatar_key:
            # Get new S3 key to compare
            new_avatar_key = get_s3_key_from_imagefield(user.avatar) if user.avatar else None
            # Only delete if keys are different (file was actually changed)
            if new_avatar_key and old_avatar_key != new_avatar_key:
                delete_old_file_from_s3(old_avatar_key)
        
        if cover_updated and old_cover_key:
            # Get new S3 key to compare
            new_cover_key = get_s3_key_from_imagefield(user.cover) if user.cover else None
            # Only delete if keys are different (file was actually changed)
            if new_cover_key and old_cover_key != new_cover_key:
                delete_old_file_from_s3(old_cover_key)
        
        # Delete old credential files that are no longer in new credentials
        if credentials_updated:
            # Get new certificates URLs
            new_credentials = teacher.credentials if hasattr(teacher, 'credentials') and teacher.credentials else {}
            new_certificates = new_credentials.get('certificates', []) if isinstance(new_credentials, dict) else []
            new_certificate_urls = {cert.get('url', '') for cert in new_certificates if cert.get('url')}
            
            # Delete old certificates that are not in new certificates
            for old_cert in old_certificates:
                old_cert_url = old_cert.get('url', '')
                if old_cert_url and old_cert_url not in new_certificate_urls:
                    # Extract S3 key from credential URL
                    old_cert_s3_key = get_s3_key_from_credential_url(old_cert_url)
                    if old_cert_s3_key:
                        delete_old_file_from_s3(old_cert_s3_key)

        # Return updated data (same structure as GET)
        # Refresh from database to get latest data
        user.refresh_from_db()
        teacher.refresh_from_db()

        # Get updated user data
        user_serializer = UserSerializer(user, context={'request': request})
        user_data = user_serializer.data

        # Get updated teacher data
        teacher_serializer = TeacherSerializer(teacher, context={'request': request})
        teacher_data = teacher_serializer.data

        # Process credentials to absolute URLs
        credentials = teacher_data.get('credentials', {})
        if credentials and 'certificates' in credentials:
            certificates = credentials['certificates']
            processed_certificates = []
            for cert in certificates:
                cert_url = cert.get('url', '')
                if cert_url:
                    absolute_url = get_absolute_media_url(cert_url, request)
                    processed_cert = cert.copy()
                    processed_cert['url'] = absolute_url
                    processed_certificates.append(processed_cert)
                else:
                    processed_certificates.append(cert)
            credentials['certificates'] = processed_certificates
            teacher_data['credentials'] = credentials

        # Merge teacher data into user data
        user_data.update(teacher_data)
        user_data['teacher_type_display'] = teacher.get_teacher_type_display()

        # Add display fields
        user_data['role_display'] = user.get_role_display()
        user_data['status_display'] = user.get_status_display()

        # Convert avatar to avatar_url
        avatar = user_data.get('avatar')
        user_data['avatar_url'] = get_absolute_media_url(avatar, request)
        user_data.pop('avatar', None)

        # Convert cover to cover_url
        cover = user_data.get('cover')
        user_data['cover_url'] = get_absolute_media_url(cover, request)
        user_data.pop('cover', None)

        return Response(
            {
                "message": "Teacher profile updated successfully",
                "data": user_data
            },
            status=status.HTTP_200_OK
        )
