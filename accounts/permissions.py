from .models import User
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied('You must be logged in to access this resource')
        
        if request.user.role != 'A':
            raise PermissionDenied('You are not an Admin. Only Admin has permission to access.')
        
        if request.user.status == 'D':
            raise PermissionDenied('Your Admin account has been disabled')
        
        return True
    
    def has_object_permission(self, request, view, obj):
        return True

