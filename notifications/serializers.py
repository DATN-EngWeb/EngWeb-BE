from rest_framework import serializers

from feedback.models import TestFeedback
from forum.models import PostComment


class TeacherNotificationSerializer(serializers.ModelSerializer):
    """Serializer for notification of Teacher (TestFeedback)"""
    type = serializers.CharField(default="F")
    test_id = serializers.IntegerField(source="test.id")
    test_name = serializers.CharField(source="test.title")
    skill = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    message = serializers.CharField(source="comment")
    created_at = serializers.DateTimeField()

    class Meta:
        model = TestFeedback
        fields = [
            "id", "type", "test_id", "test_name", "skill",
            "author", "message", "is_read", "created_at"
        ]

    def get_skill(self, obj):
        if obj.test:
            return obj.test.get_skill_display()
        return None

    def get_author(self, obj):
        if obj.teacher and obj.teacher.user:
            return {
                "name": obj.teacher.user.full_name or obj.teacher.user.username,
                "avatar": self._get_avatar_url(obj.teacher.user.avatar),
            }
        return {
            "name": "Unknown",
            "avatar": None,
        }

    def _get_avatar_url(self, avatar):
        if avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(avatar.url)
            return avatar.url
        return None


class StudentNotificationSerializer(serializers.ModelSerializer):
    """Serializer for notification of Student (PostComment)"""
    type = serializers.CharField(default="C")
    post_id = serializers.IntegerField(source="post.id")
    post_title = serializers.CharField(source="post.title")
    skill = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()
    message = serializers.CharField(source="content")
    created_at = serializers.DateTimeField()

    class Meta:
        model = PostComment
        fields = [
            "id", "type", "post_id", "post_title", "skill",
            "author", "message", "is_read", "created_at"
        ]

    def get_skill(self, obj):
        if obj.post and obj.post.productive_test_history:
            prod_test = obj.post.productive_test_history.productive_test
            if prod_test and prod_test.test:
                return prod_test.test.get_skill_display()
        return None

    def get_author(self, obj):
        if obj.user:
            return {
                "name": obj.user.full_name or obj.user.username,
                "avatar": self._get_avatar_url(obj.user.avatar),
            }
        return {
            "name": "Unknown",
            "avatar": None,
        }

    def _get_avatar_url(self, avatar):
        if avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(avatar.url)
            return avatar.url
        return None
