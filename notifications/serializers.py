from rest_framework import serializers
from .models import Notification


class NotificationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "type", "title", "content", "is_read", "created_at"]
        read_only_fields = fields
