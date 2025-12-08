from .models import User, Teacher, Student

from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers

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
    user = UserSerializer(required=False)

    class Meta:
        model = Teacher
        fields = [
            'user', 
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