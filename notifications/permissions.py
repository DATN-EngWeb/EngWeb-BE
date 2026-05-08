from rest_framework.permissions import BasePermission


class IsNotificationOwner(BasePermission):
    """
    Teacher: Only teacher who created the test can mark the feedback as read
    Student: Only student who posted the post can mark the comment as read
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        # TestFeedback
        if hasattr(obj, "test"):
            return user == obj.test.created_by.user

        # PostComment
        if hasattr(obj, "post"):
            return user == obj.post.productive_test_history.student.user

        return False
