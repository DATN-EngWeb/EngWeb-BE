from django.urls import path

from .views import (
    PostListCreateAPIView,
    StudentRetrieveUpdateDeletePostAPIView,
    PostCommentListCreateAPIView,
    UserRetrieveUpdateDeleteCommentAPIView,
    PostReactionAPIView,
)

urlpatterns = [
    # Posts endpoints
    path("posts", PostListCreateAPIView.as_view(), name="post-list-create"),
    path("posts/<int:post_id>", StudentRetrieveUpdateDeletePostAPIView.as_view(), name="post-retrieve-update-delete"),
    
    # Comments endpoints
    path("comments", PostCommentListCreateAPIView.as_view(), name="comment-list-create"),
    path("comments/<int:comment_id>", UserRetrieveUpdateDeleteCommentAPIView.as_view(), name="comment-retrieve-update-delete"),

    # Reactions endpoints
    path("reactions/<int:post_id>", PostReactionAPIView.as_view(), name="user-toggle-post-like"),
]
