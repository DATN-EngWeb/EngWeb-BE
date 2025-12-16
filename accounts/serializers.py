from .models import User, Teacher, Student
from .utils import (
    create_otp_code,
    cache_register_otp,
    send_registration_otp_email,
    get_absolute_media_url,
)

from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.db.models import Q

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        """
        - AbstractUser has 'groups' and 'user_permissions'
        - If we use 'fields = "__all__"', when data is received from client:
            + If data is sent as JSON and don't have these fields, Django use JSONParser.
            JsonParser won't create many-to-many fields.
            + If data is sent as FormData, Django use MultiPartParser.
            MultiPartParser will create empty lists for many-to-many fields. -> errors
        """
        exclude = ['groups', 'user_permissions']
        extra_kwargs = {
            'id': {'read_only': True},
            'password': {'write_only': True},
            'date_joined': {'read_only': True},
            'last_login': {'read_only': True},
            'role': {'read_only': True},
            'status': {'read_only': True},
            'is_active': {'read_only': True},
            'updated_at': {'read_only': True},
        }

    def validate(self, attrs):
        if attrs.get('password'):
            try:
                validate_password(attrs['password'])  # django password built-in validator
            except ValidationError as e:
                raise serializers.ValidationError({'password': list(e.messages)})
        
        return attrs
    
    def create(self, validated_data):
        role = self.initial_data.get('role', '').upper()
        validated_data['role'] = role
        validated_data['status'] = 'P'
        user = User.objects.create_user(**validated_data)
        
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        
        return instance

class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = [
            'current_workplace', 
            'teacher_type', 
            'experience_year', 
            'introduction', 
            'credentials'
        ]
        extra_kwargs = {
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }

    def validate(self, attrs):
        required_teacher_fields = ['current_workplace', 'teacher_type', 'introduction']
        errors = {}

        # Validate teacher fields
        for field in required_teacher_fields:
            value = attrs.get(field)
            if isinstance(value, str):
                value = value.strip()
            if not value:
                errors[field] = 'This field is required.'
        
        # Validate teacher_type values
        teacher_type = attrs.get('teacher_type')
        if teacher_type and teacher_type not in ['S', 'C', 'F']:
            errors['teacher_type'] = 'Must be one of: S (School Teacher), C (Center Teacher), F (Freelance Teacher).'
        
        # Validate experience_year
        experience_year = attrs.get('experience_year')
        if experience_year is None:
            errors['experience_year'] = 'This field is required.'
        elif isinstance(experience_year, str):
            try:
                attrs['experience_year'] = int(experience_year)
            except ValueError:
                errors['experience_year'] = 'Must be a valid integer.'
        elif not isinstance(experience_year, int) or experience_year < 0:
            errors['experience_year'] = 'Must be a non-negative integer.'
        
        # Validate credentials - at least one certificate required
        credentials = attrs.get('credentials', {})
        if not credentials or not isinstance(credentials, dict):
            errors['credentials'] = 'Credentials data is required.'
        elif not credentials.get('certificates') or len(credentials.get('certificates', [])) == 0:
            errors['credentials'] = 'At least one certificate is required.'

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        user = self.context.get('user')
        
        if not user:
            raise serializers.ValidationError({'user': 'User context is required for teacher creation.'})

        # User is already updated in view, just create teacher
        teacher = Teacher.objects.create(user=user, **validated_data)
        return teacher

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user

        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=False)

    class Meta:
        model = Student
        fields = ['user'] # other fields are updated by code logic not by api data 

    def create(self, validated_data):
        user = self.context.get('user')
        
        if not user:
            raise serializers.ValidationError({'user': 'User is required in context'})

        if Student.objects.filter(user=user).exists():
            return Student.objects.get(user=user)
        
        student = Student.objects.create(user=user)
        return student

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user

        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Login serializer with status-based flows:
    - P: re-send OTP, ask FE to verify
    - I: ask FE to complete profile (upload certificate)
    - W: waiting for admin approval
    - V: issue tokens
    - D: disabled account
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        return token

    def authenticate_user(self, identifier, password):
        try:
            user = get_user_model().objects.get(Q(username=identifier) | Q(email=identifier))
            if user.check_password(password):
                return user
        except get_user_model().DoesNotExist:
            return None

    def validate(self, attrs):
        identifier = attrs.get('username')
        password = attrs.get('password')

        # 1) Check username/email + password
        user = self.authenticate_user(identifier, password)
        if not user:
            raise serializers.ValidationError('Invalid username/email or password.')

        # 2) Check is_active
        if not user.is_active:
            raise serializers.ValidationError({'detail': 'Account is deactivated.', 'status': 'D'})

        status_code = getattr(user, 'status', None)

        # Admin login flow - only allow status V
        if user.role == 'A':
            if status_code != 'V':
                raise serializers.ValidationError({
                    'detail': 'Please contact the development team for assistance.',
                    'status': status_code,
                })
            # Admin with status V -> issue tokens
            refresh = self.get_token(user)
            access = refresh.access_token
            update_last_login(None, user)

            # Get request from context if available (for building absolute URL)
            request = self.context.get('request') if hasattr(self, 'context') else None
            return {
                'refresh': str(refresh),
                'access': str(access),
                'status': status_code,
                'username': user.username,
                'avatar': get_absolute_media_url(user.avatar, request),
            }

        # 3) Pending verification -> resend OTP
        if status_code == 'P':
            otp_code = create_otp_code()
            cache_register_otp(user.id, otp_code, user.email)
            send_registration_otp_email(user.email, otp_code)
            raise serializers.ValidationError({
                'detail': 'Account is not verified yet. OTP sent to your email.',
                'user_id': user.id,
                'status': status_code,
                'require_verification': True,
            })

        # 4) Incomplete profile (teacher)
        if status_code == 'I':
            raise serializers.ValidationError({
                'detail': 'Please complete your profile (upload certificates).',
                'user_id': user.id,
                'status': status_code,
                'require_certificate': True,
            })

        # 5) Waiting approval
        if status_code == 'W':
            raise serializers.ValidationError({
                'detail': 'Account pending approval. Please wait for admin review.',
                'user_id': user.id,
                'status': status_code,
            })

        # 7) Disabled
        if status_code == 'D':
            raise serializers.ValidationError({
                'detail': 'Account has been disabled.',
                'user_id': user.id,
                'status': status_code,
            })

        # 6) Verified -> issue tokens
        refresh = self.get_token(user)
        access = refresh.access_token
        update_last_login(None, user)

        # Get request from context if available (for building absolute URL)
        request = self.context.get('request') if hasattr(self, 'context') else None
        return {
            'refresh': str(refresh),
            'access': str(access),
            'status': status_code,
            'username': user.username,
            'avatar': get_absolute_media_url(user.avatar, request),
        }


class AdminUserSerializer(serializers.ModelSerializer):
    """
    Serializer for Admin Dashboard - List Users
    Returns: id, username, email, avatar_url, role, role_display, date_joined, status, status_display
    """
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'avatar_url',
            'role',
            'role_display',
            'date_joined',
            'status',
            'status_display',
        ]
        # Use read_only_fields for simplicity since we only need read_only=True
        # All these fields should not be modified through this serializer
        read_only_fields = ['id', 'username', 'email', 'role', 'date_joined', 'status']

    def get_avatar_url(self, obj):
        """
        Build absolute URL for avatar image using helper function.
        
        Why build_absolute_uri?
        - obj.avatar.url returns relative path: /media/avatars/user.jpg
        - Frontend needs full URL: http://localhost:8000/media/avatars/user.jpg
        - build_absolute_uri() creates complete URL from request
        """
        request = self.context.get('request')
        return get_absolute_media_url(obj.avatar, request)