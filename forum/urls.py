from django.urls import path

from .views import (
    StudentCreatePostAPIView,
    UserRetrieveTestPostAPIView,
    UserRetrievePostCommentAPIView,
    UserCreatePostCommentAPIView,
    PostReactionAPIView,
    StudentUpdateDeletePostAPIView,
    UserUpdateDeleteCommentAPIView,
)

urlpatterns = [
    # Posts endpoints
    path("posts", StudentCreatePostAPIView.as_view(), name="student-create-post"),
    path("posts/<int:test_id>", UserRetrieveTestPostAPIView.as_view(), name="user-retrieve-test-post"),
    path("posts-update-delete/<int:post_id>", StudentUpdateDeletePostAPIView.as_view(), name="student-manage-post"),
    
    # Comments endpoints
    path("comments/<int:post_id>", UserRetrievePostCommentAPIView.as_view(), name="user-retrieve-post-comments"),
    path("comments-create/<int:post_id>", UserCreatePostCommentAPIView.as_view(), name="user-create-post-comment"),
    path("comments-update-delete/<int:comment_id>", UserUpdateDeleteCommentAPIView.as_view(), name="user-manage-comment"),

    # Reactions endpoints
    path("reactions/<int:post_id>", PostReactionAPIView.as_view(), name="user-toggle-post-like"),
]
