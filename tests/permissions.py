from rest_framework import permissions


class IsTeacher(permissions.BasePermission):
    """
    Custom permission to check if user is a teacher
    """
    message = 'Only teachers can perform this action.'

    def has_permission(self, request, view):
        """
        Check if user is authenticated and is a teacher
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            getattr(request.user, 'teacher', None) is not None
        )

    def has_object_permission(self, request, view, obj):
        """
        Check if teacher is the creator of the test
        Used for: Update test, Delete test, etc.
        
        - GET: Allow all authenticated teachers to view any test
        - POST, PUT, PATCH, DELETE: Only creator can modify
        """
        # Allow GET for all authenticated teachers
        if request.method == 'GET':
            return True
        
        # For modify operations (POST, PUT, PATCH, DELETE)
        # Only the creator teacher can modify their test
        return obj.created_by == request.user.teacher


class IsAdminOrOwner(permissions.BasePermission):
    """
    Custom permission to check if user is admin or the owner (creator) of the test
    """
    message = 'Only admin or the owner can perform this action.'

    def has_permission(self, request, view):
        """
        Check if user is authenticated
        """
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Check if user is admin or the creator of the test
        """
        # Allow if user is admin
        if request.user.role == 'A':
            return True
        
        # Allow if user is the teacher who created the test
        if hasattr(request.user, 'teacher') and obj.created_by == request.user.teacher:
            return True
        
        return False
