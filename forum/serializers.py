from rest_framework import serializers

from .models import Post, PostComment, PostReaction
from test_histories.models import ProductiveTestHistory

class PostListSerializer(serializers.ModelSerializer):
    # Get user info
    author_name = serializers.CharField(source="productive_test_history.student.user.full_name", read_only=True)
    author_avatar = serializers.ImageField(source="productive_test_history.student.user.avatar", read_only=True)
    
    # Get test info
    skill = serializers.CharField(source="productive_test_history.productive_test.test.get_skill_display", read_only=True)
    
    # Get student submission info
    audio_path = serializers.CharField(source="productive_test_history.audio_path", read_only=True)
    user_answer_text = serializers.CharField(source="productive_test_history.user_answer_text", read_only=True)
    
    # Use annotation for is_liked
    is_liked = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = Post
        fields = [
            "id", "title", "description", "like_count", "comment_count", "created_at",
            "author_name", "author_avatar", "skill", "audio_path", "user_answer_text", "is_liked"
        ]


class PostCreateSerializer(serializers.ModelSerializer):
    productive_test_history_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Post
        fields = ["id", "productive_test_history_id", "title", "description"]

    def validate(self, attrs):
        history_id = attrs.get("productive_test_history_id")

        try:
            history = ProductiveTestHistory.objects.get(id=history_id)
        except ProductiveTestHistory.DoesNotExist:
            raise serializers.ValidationError("Valid productive test history not found.")

        # Only allow sharing submitted tests
        if history.type != "S":
            raise serializers.ValidationError("You can only share submitted tests.")

        # Check if this post has already been shared
        if Post.objects.filter(productive_test_history=history).exists():
            raise serializers.ValidationError("A post already exists for this test submission.")

        attrs["productive_test_history"] = history
        return attrs

    def create(self, validated_data):
        validated_data.pop("productive_test_history_id", None)
        return super().create(validated_data)


class PostUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ["title", "description"]


class PostCommentListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="user.full_name", read_only=True)
    author_avatar = serializers.ImageField(source="user.avatar", read_only=True)

    class Meta:
        model = PostComment
        fields = [
            "id",
            "content",
            "created_at",
            "updated_at",
            "author_name",
            "author_avatar",
        ]


class PostCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostComment
        fields = ["id", "content"]


class PostCommentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostComment
        fields = ["content"]
