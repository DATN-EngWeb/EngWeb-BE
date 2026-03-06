from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

from test_histories.models import ProductiveTestHistory

class IsOwner(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            raise PermissionDenied("You must be logged in to access this resource.")

        if request.user.status != "V":
            raise PermissionDenied("Your account need to be verified.")

        if request.user.role != "S":
            raise PermissionDenied("Only students can perform this action.")

        # Check if the history belongs to the requesting student for POST method
        if request.method == "POST":
            history_id = request.data.get("productive_test_history_id")

            if history_id:
                try:
                    history = ProductiveTestHistory.objects.get(id=history_id)
                    
                    if history.student.user_id != request.user.id:
                        raise PermissionDenied("You can only share your own test histories.")
                except ProductiveTestHistory.DoesNotExist:
                    pass

        return True
