from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied("You must be logged in to access this resource.")

        if request.user.role != "T":
            raise PermissionDenied("Only teachers can access this resource.")
            
        if request.user.status != "V":
            raise PermissionDenied("Your teacher account needs to be verified.")

        return True
