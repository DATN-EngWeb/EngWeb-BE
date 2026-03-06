from django.urls import path

from .views import (
    StudentCreatePostAPIView,
    UserRetrieveTestPostAPIView,
    UserRetrievePostCommentAPIView,
    UserCreatePostCommentAPIView,
    PostReactionAPIView,
)

urlpatterns = [
    # Posts endpoints
    path("posts", StudentCreatePostAPIView.as_view(), name="student-create-post"),
    path("posts/<int:test_id>", UserRetrieveTestPostAPIView.as_view(), name="user-retrieve-test-post"),
    
    # Comments endpoints
    path("comments/<int:post_id>", UserRetrievePostCommentAPIView.as_view(), name="user-retrieve-post-comments"),
    path("comments-create/<int:post_id>", UserCreatePostCommentAPIView.as_view(), name="user-create-post-comment"),

    # Reactions endpoints
    path("reactions/<int:post_id>", PostReactionAPIView.as_view(), name="user-toggle-post-like"),
]
