from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied


class IsOwnerOrAdmin(BasePermission):
    """
    Permission class that allows:
    - Admin users to access all histories
    - Student users to access only their own histories
    """

    def has_permission(self, request, view):
        """Check if user is authenticated and verified"""
        if not request.user.is_authenticated:
            raise PermissionDenied("You must be logged in to access this resource.")

        if request.user.status != "V":
            raise PermissionDenied("Your account needs to be verified.")

        # Admin and Student can access
        if request.user.role in ["A", "S"]:
            return True

        raise PermissionDenied("Only students and admins can access test histories.")

    def has_object_permission(self, request, view, obj):
        """Check if user can access this specific history object"""
        # Admin can access all
        if request.user.role == "A":
            return True

        # Student can only access their own history
        if request.user.role == "S":
            # Check if the student in the history matches the current user's student profile
            return (
                hasattr(request.user, "student")
                and obj.student.pk == request.user.student.pk
            )

        return False


class IsStudent(BasePermission):
    """
    Permission class that only allows students to create test history
    """

    def has_permission(self, request, view):
        """Check if user is authenticated, verified and is a student"""
        if not request.user.is_authenticated:
            raise PermissionDenied("You must be logged in to access this resource.")

        if request.user.status != "V":
            raise PermissionDenied("Your account needs to be verified.")

        if request.user.role != "S":
            raise PermissionDenied("Only students can create test history.")
        
        if not hasattr(request.user, "student"):
            raise PermissionDenied("Student profile not found.")

        return True
