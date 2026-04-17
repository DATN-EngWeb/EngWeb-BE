from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if obj.user != request.user:
            raise PermissionDenied("You can only access your own notifications.")
        return True
