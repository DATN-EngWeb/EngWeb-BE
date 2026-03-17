from rest_framework import serializers
from .models import TestFeedback
from tests.models import Test

class TestFeedbackListSerializer(serializers.ModelSerializer):
    author_id = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()

    class Meta:
        model = TestFeedback
        fields = [
            "id",
            "test",
            "comment",
            "created_at",
            "updated_at",
            "created_by",
            "author_id",
            "author_name",
            "author_avatar",
        ]

    def get_author_id(self, obj):
        if obj.created_by == "A":
            return None
        if obj.teacher and obj.teacher.user:
            return obj.teacher.user.id
        return None

    def get_author_name(self, obj):
        if obj.created_by == "A":
            return "NENS AI"
        elif obj.teacher and obj.teacher.user:
            return obj.teacher.user.full_name
        return "Unknown"

    def get_author_avatar(self, obj):
        if obj.created_by == "A":
            return None
        elif obj.teacher and obj.teacher.user and obj.teacher.user.avatar:
            request = self.context.get("request")
            if request and hasattr(request, "build_absolute_uri"):
                return request.build_absolute_uri(obj.teacher.user.avatar.url)
            return obj.teacher.user.avatar.url
        return None

class TeacherTestFeedbackCreateSerializer(serializers.ModelSerializer):
    test_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = TestFeedback
        fields = ["id", "test_id", "comment"]

    def validate(self, attrs):
        test_id = attrs.get("test_id")
        try:
            test = Test.objects.get(id=test_id)
        except Test.DoesNotExist:
            raise serializers.ValidationError({"test_id": "Valid test not found."})

        attrs["test"] = test
        return attrs

    def create(self, validated_data):
        validated_data.pop("test_id", None)
        return super().create(validated_data)

class TeacherTestFeedbackUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestFeedback
        fields = ["comment"]
