from .models import User, Teacher, Student

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied("You must be logged in to access this resource.")

        if request.user.role != "A":
            raise PermissionDenied("Only Admin has permission to access.")

        if request.user.status != "V":
            raise PermissionDenied("Your Admin account need to be verified.")

        return True

    def has_object_permission(self, request, view, obj):
        return True

class IsOwner(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied("You must be logged in to access this resource.")

        if request.user.status != "V":
            raise PermissionDenied("Your account need to be verified.")
        return True

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, User):
            return obj.id == request.user.id

        if isinstance(obj, Teacher) or isinstance(obj, Student):
            return obj.user_id == request.user.id

        return False

class IsOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied("You must be logged in to access this resource.")

        if request.user.status != "V":
            raise PermissionDenied("Your Admin account need to be verified.")

        if request.user.role != "A":
            raise PermissionDenied("Only Admin has permission to access.")

        return True

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, User):
            return (obj.id == request.user.id) or (obj.role != "A")

        return False
