from .models import User, Teacher, Student
from .utils import (
    create_otp_code,
    cache_register_otp,
    send_registration_otp_email,
    get_absolute_media_url
)

from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.core.exceptions import ValidationError
from django.db.models import Q

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ["groups", "user_permissions"]
        extra_kwargs = {
            "id": {"read_only": True},
            "password": {"write_only": True},
            "date_joined": {"read_only": True},
            "last_login": {"read_only": True},
            "role": {"read_only": True},
            "status": {"read_only": True},
            "is_active": {"read_only": True},
            "updated_at": {"read_only": True}
        }

    def validate(self, attrs):
        if attrs.get("password"):
            try:
                validate_password(attrs["password"])
            except ValidationError as e:
                raise serializers.ValidationError({"password": list(e.messages)})

        return attrs

    def create(self, validated_data):
        role = self.initial_data.get("role", "").upper()
        validated_data["role"] = role
        validated_data["status"] = "P"
        user = User.objects.create_user(**validated_data)

        if role == "S":
            Student.objects.create(user=user)

        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)
        instance.save()

        return instance

class TeacherSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Teacher
        fields = [
            "user",
            "current_workplace",
            "teacher_type",
            "experience_year",
            "introduction",
            "credentials",
            "created_at",
            "updated_at"
        ]
        extra_kwargs = {
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }

    def validate(self, attrs):
        errors = {}
        is_create = self.instance is None  # True if creating new, False if updating

        # Only require these fields when creating (POST), not when updating (PATCH)
        if is_create:
            required_teacher_fields = ["current_workplace", "teacher_type", "introduction"]

        for field in required_teacher_fields:
            value = attrs.get(field)

            if isinstance(value, str):
                value = value.strip()
            
            if not value:
                errors[field] = "This field is required."

            # Validate experience_year - required only on create
        experience_year = attrs.get("experience_year")
        if experience_year is None:
            errors["experience_year"] = "This field is required."
        elif isinstance(experience_year, str):
            try:
                attrs["experience_year"] = int(experience_year)
            except ValueError:
                errors["experience_year"] = "Must be a valid integer."
        elif not isinstance(experience_year, int) or experience_year < 0:
            errors["experience_year"] = "Must be a non-negative integer."

            # Validate credentials - required only on create
        credentials = attrs.get("credentials", None)
        if not isinstance(credentials, list) or len(credentials) == 0 or len(credentials) > 3:
            errors["credentials"] = "At least one credential is required and maximum 3 credentials are allowed."
        else:
            # When updating, validate only if fields are provided
            # Validate experience_year if provided
            experience_year = attrs.get("experience_year")
            if experience_year is not None:
                if isinstance(experience_year, str):
                    try:
                        attrs["experience_year"] = int(experience_year)
                    except ValueError:
                        errors["experience_year"] = "Must be a valid integer."
                elif not isinstance(experience_year, int) or experience_year < 0:
                    errors["experience_year"] = "Must be a non-negative integer."

            # Validate credentials if provided
            credentials = attrs.get("credentials", None)
            if credentials is not None:
                if not isinstance(credentials, list) or len(credentials) == 0 or len(credentials) > 3:
                    errors["credentials"] = "At least one credential is required and maximum 3 credentials are allowed."

        # Validate teacher_type if provided (for both create and update)
        teacher_type = attrs.get("teacher_type")
        if teacher_type and teacher_type not in ["S", "C", "F"]:
            errors["teacher_type"] = (
                "Must be one of: S (School Teacher), C (Center Teacher), F (Freelance Teacher)."
            )

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        teacher = Teacher.objects.create(**validated_data)
        return teacher

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        user = instance.user

        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

class StudentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Student
        fields = [
            "user",
            "cumulative_point",
            "weekly_point",
            "weekly_ai_turn",
            "bonus_ai_turn",
            "completed_test",
            "qualified_test",
            "last_attempt_at",
            "streak_count",
            "max_streak",
            "level",
            "title",
            "created_at",
            "updated_at"
        ]
        extra_kwargs = {
            "cumulative_point": {"read_only": True},
            "weekly_point": {"read_only": True},
            "weekly_ai_turn": {"read_only": True},
            "bonus_ai_turn": {"read_only": True},
            "completed_test": {"read_only": True},
            "qualified_test": {"read_only": True},
            "last_attempt_at": {"read_only": True},
            "streak_count": {"read_only": True},
            "max_streak": {"read_only": True},
            "level": {"read_only": True},
            "title": {"read_only": True},
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def authenticate_user(self, identifier, password):
        try:
            user = get_user_model().objects.get(
                Q(username=identifier) | Q(email=identifier)
            )
            if user.check_password(password):
                return user
        except get_user_model().DoesNotExist:
            return None

    def validate(self, attrs):
        identifier = attrs.get("username")
        password = attrs.get("password")
        user = self.authenticate_user(identifier, password)

        if not user:
            raise serializers.ValidationError("Invalid username/email or password.")

        if not user.is_active:
            raise serializers.ValidationError({"detail": "Account is deactivated.", "status": "D"})

        status_code = getattr(user, "status", None)

        # admin login flow - only allow status V
        if user.role == "A":
            if status_code != "V":
                raise serializers.ValidationError({
                        "detail": "Please contact the development team for assistance.",
                        "status": status_code,
                    })

            # admin with status V -> issue tokens
            refresh = self.get_token(user)
            access = refresh.access_token
            update_last_login(None, user)
            response = {
                "refresh": str(refresh),
                "access": str(access),
                "status": status_code,
                "username": user.username,
                "avatar": get_absolute_media_url(user.avatar)
            }

            return response

        # pending verification -> resend OTP
        if status_code == "P":
            otp_code = create_otp_code()
            cache_register_otp(user.id, otp_code, user.email)
            send_registration_otp_email(user.email, otp_code)

            raise serializers.ValidationError(
                {
                    "detail": "Account is not verified yet. OTP sent to your email.",
                    "user_id": user.id,
                    "status": status_code,
                    "require_verification": True
                }
            )

        # incomplete profile (teacher)
        if status_code == "I":
            raise serializers.ValidationError(
                {
                    "detail": "Please complete your profile (upload certificates).",
                    "user_id": user.id,
                    "status": status_code,
                    "require_certificate": True
                }
            )

        # waiting approval
        if status_code == "W":
            raise serializers.ValidationError(
                {
                    "detail": "Account pending approval. Please wait for admin review.",
                    "user_id": user.id,
                    "status": status_code
                }
            )

        # disabled
        if status_code == "D":
            raise serializers.ValidationError(
                {
                    "detail": "Account has been disabled.",
                    "user_id": user.id,
                    "status": status_code,
                }
            )

        # verified -> issue tokens
        refresh = self.get_token(user)
        access = refresh.access_token
        update_last_login(None, user)
        response = {
            "refresh": str(refresh),
            "access": str(access),
            "status": status_code,
            "username": user.username,
            "avatar": get_absolute_media_url(user.avatar)
        }

        return response
