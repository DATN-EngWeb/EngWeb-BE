from django.db.models import Exists, OuterRef
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import F
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from rest_framework import generics, permissions, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import status

from accounts.authentication import CustomTokenAuthentication
from .models import Post, PostComment, PostReaction
from .serializers import (
    PostListSerializer, 
    PostCreateSerializer, 
    PostUpdateSerializer,
    PostCommentListSerializer, 
    PostCommentCreateSerializer,
    PostCommentUpdateSerializer,
)
from .permissions import IsOwner

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, inline_serializer
from textwrap import dedent

class UserUpdateDeleteCommentAPIView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    serializer_class = PostCommentUpdateSerializer
    lookup_field = "id"
    lookup_url_kwarg = "comment_id"

    def get_queryset(self):
        return PostComment.objects.select_related("user").all()

    @extend_schema(
        summary="Retrieve a comment",
        description="Retrieves the details of a specific comment.",
        tags=["comments"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update a comment (Not Allowed)",
        description="PUT method is not supported. Please use PATCH instead.",
        tags=["comments"],
        responses={
            405: OpenApiResponse(description="Method not allowed"),
        }
    )
    def put(self, request, *args, **kwargs):
        return Response(
            {"detail": "PUT method is not supported. Please use PATCH for updates."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @extend_schema(
        summary="Partially update a comment",
        description=dedent("""\
            Allows a user to partially update the content of a comment they own.
            
            ### Example Test Case (2.1)
            * **URL:** `/api/forums/comments-update-delete/10`
            * **Method:** `PATCH`
            * **Auth:** Bearer Token (e.g., Student 4 owning Comment 10)
            * **Body:** `{"content": "I changed my mind, this post is awesome!"}`
            * **Result:** Returns `200 OK` and the comment's content is updated.
        """),
        tags=["comments"],
        responses={
            200: OpenApiResponse(description="Successfully updated the comment"),
            400: OpenApiResponse(description="Bad request"),
            403: OpenApiResponse(description="Forbidden (Not the owner)"),
            404: OpenApiResponse(description="Comment not found"),
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a comment",
        description=dedent("""\
            Allows a user to delete a comment they own. This will safely decrement the parent post's comment count.
            
            ### Example Test Case (2.3)
            * **URL:** `/api/forums/comments-update-delete/10`
            * **Method:** `DELETE`
            * **Auth:** Bearer Token (e.g., Student 4 owning Comment 10)
            * **Result:** Returns `204 No Content`. The comment is deleted and the parent post's `comment_count` decreases by 1.
        """),
        tags=["comments"],
        responses={
            204: OpenApiResponse(description="Successfully deleted the comment"),
            403: OpenApiResponse(description="Forbidden (Not the owner)"),
            404: OpenApiResponse(description="Comment not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # Save reference to post before deleting comment
        post = instance.post
        
        # Delete comment
        super().perform_destroy(instance)
        
        # Safely decrement comment_count
        post.comment_count = F('comment_count') - 1
        post.save(update_fields=['comment_count'])

class ForumPagination(PageNumberPagination):
    page_size = 2
    page_size_query_param = "page_size"
    max_page_size = 10

class StudentCreatePostAPIView(generics.CreateAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsOwner]
    serializer_class = PostCreateSerializer

    @extend_schema(
        summary="Create a new forum post",
        description="Allows a student to share their submitted productive test (Writing or Speaking) to the forum.",
        tags=["posts"],
        responses={
            201: OpenApiResponse(description="Post created successfully"),
            400: OpenApiResponse(description="Bad request, validation error"),
            403: OpenApiResponse(description="Permission denied, token expired or not a student"),
        },
        examples=[
            OpenApiExample(
                "Successful creation",
                request_only=True,
                value={
                    "productive_test_history_id": 1,
                    "title": "My Writing Task",
                    "description": "Please give me feedback!"
                }
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class UserRetrieveTestPostAPIView(generics.ListAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [permissions.AllowAny]
    pagination_class = ForumPagination
    serializer_class = PostListSerializer
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title"]
    ordering_fields = ["created_at", "like_count", "comment_count"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = Post.objects.select_related(
            "productive_test_history",
            "productive_test_history__student__user",
            "productive_test_history__productive_test__test"
        )
        
        test_id = self.kwargs.get("test_id")
            
        if test_id:
            queryset = queryset.filter(productive_test_history__productive_test__test_id=test_id)

        # Handle filter?filter=mine for the "Your Posts" tab
        filter_type = self.request.query_params.get("filter")
        
        if filter_type == "mine" and self.request.user.is_authenticated and self.request.user.role == "S":
            queryset = queryset.filter(productive_test_history__student__user=self.request.user)

        # Handle the is_liked field if the viewer is logged in
        if self.request.user.is_authenticated:
            is_liked_subquery = PostReaction.objects.filter(
                post=OuterRef("pk"), user=self.request.user, status="L"
            )
            queryset = queryset.annotate(is_liked=Exists(is_liked_subquery))

        return queryset

    @extend_schema(
        summary="Retrieve forum posts for a specific test",
        tags=["posts"],
        description=dedent("""\
            Retrieves a paginated list of forum posts shared for a particular test. 
            Returns additional `is_liked` metadata for authenticated viewers.

            ### Test Cases & Examples

            **1. Get all posts for a test (Unauthenticated)**
            * **URL:** `/api/forums/posts/3`
            * **Auth:** None
            * **Result:** Returns all posts belonging to `ProductiveTest` history for test ID 3. The `is_liked` field defaults to `false`.

            **2. View Like status (Authenticated)**
            * **URL:** `/api/forums/posts/3`
            * **Auth:** Bearer Token
            * **Result:** Similar to Case 1, but `is_liked` dynamically returns `true` or `false` based on the current user's reactions.

            **3. Filter by "Your Posts" tab**
            * **URL:** `/api/forums/posts/3?filter=mine`
            * **Auth:** Bearer Token (Must be a Student)
            * **Result:** Returns only the posts shared by the currently logged-in student.

            **4. Search by title**
            * **URL:** `/api/forums/posts/4?search=Short`
            * **Auth:** Optional
            * **Result:** Finds posts for test ID 4 where the title or description contains the word "Short".

            **5. Ordering (Newest vs Most Liked)**
            * **Newest (Default):** `/api/forums/posts/3` (ordered by `-created_at`)
            * **Most Liked:** `/api/forums/posts/3?ordering=-like_count` (orders posts with the highest likes first)

            **6. Pagination**
            * **URL:** `/api/forums/posts/3?page=1&page_size=1`
            * **Result:** Returns only 1 post per page, along with pagination metadata (`count`, `next`, `previous`).
        """),
        responses={
            200: OpenApiResponse(description="Successfully retrieved posts"),
            400: OpenApiResponse(description="Bad request, validation error"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class UserCreatePostCommentAPIView(generics.CreateAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PostCommentCreateSerializer

    @extend_schema(
        summary="Create a comment on a post",
        description="Allows any authenticated user to add a comment to a specific forum post.",
        tags=["comments"],
        responses={
            201: OpenApiResponse(description="Comment created successfully"),
            400: OpenApiResponse(description="Bad request, validation error"),
            404: OpenApiResponse(description="Post not found"),
        },
        examples=[
            OpenApiExample(
                "Successful comment",
                request_only=True,
                value={"content": "Great conclusion, but try to paraphrase the prompt more."}
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        post_id = self.kwargs.get("post_id")
        post = get_object_or_404(Post, id=post_id)
        
        # Save comment
        serializer.save(user=self.request.user, post=post)
        
        # Increment comment count safely
        post.comment_count = F("comment_count") + 1
        post.save(update_fields=["comment_count"])

class UserRetrievePostCommentAPIView(generics.ListAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ForumPagination
    serializer_class = PostCommentListSerializer
    
    # We only sort by created_at as requested, no search/filter required here
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at"]
    ordering = ["created_at"]

    def get_queryset(self):
        post_id = self.kwargs.get("post_id")
        return PostComment.objects.select_related("user").filter(post_id=post_id)

    @extend_schema(
        summary="Retrieve comments for a specific post",
        tags=["comments"],
        description=dedent("""\
            Retrieves a paginated list of comments for a given post, ordered oldest to newest by default.

            ### Test Cases & Examples

            **1. Get comments list (Default)**
            * **URL:** `/api/forums/comments/1`
            * **Auth:** Bearer Token
            * **Result:** Returns the first few comments of Post 1 (ordered by oldest first).

            **2. Reverse ordering (Newest first)**
            * **URL:** `/api/forums/comments/1?ordering=-created_at`
            * **Auth:** Bearer Token
            * **Result:** Returns comments for Post 1, but with the most recently created comments at the top.

            **3. Pagination (Custom page size)**
            * **URL:** `/api/forums/comments/1?page=2&page_size=5`
            * **Auth:** Bearer Token
            * **Result:** Skips the first page and returns the next 5 comments (e.g., comments 6 to 10).

            **4. Not Found / Unauthorized Handling**
            * **URL (Not Found):** `/api/forums/comments/999` -> Returns empty list (post doesn't exist or has no comments).
            * **Auth (Unauthorized):** Missing/Invalid Token -> Returns `401 Unauthorized`.
        """),
        responses={
            200: OpenApiResponse(description="Successfully retrieved comments"),
            400: OpenApiResponse(description="Bad request"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)



@method_decorator(
    ratelimit(key="user", rate="3/s", method=["POST"], block=False),
    name="dispatch",
)
class PostReactionAPIView(generics.GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Toggle like/unlike on a post",
        description="Creates or updates a user's reaction to a forum post. Returns the updated status ('L' for Like, 'U' for Unlike). Rate-limited to 3 requests per second per user.",
        tags=["reactions"],
        responses={
            200: OpenApiResponse(description="Successfully toggled reaction"),
            404: OpenApiResponse(description="Post not found"),
            429: OpenApiResponse(description="Too many requests"),
        }
    )
    def post(self, request, post_id):
        # 1. Rate Limiting Check: Blocks requests if the user exceeds 3 requests/second
        if getattr(request, "limited", False):
            return Response(
                {"detail": "Too many requests. Please slow down."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            
        # 2. Fetch the Post, returning 404 if it doesn't exist
        post_obj = get_object_or_404(Post, id=post_id)
        
        # 3. get_or_create: Safely fetche existing reaction, or creates a new one 
        # with default status 'L' (Like) if it doesn't exist. This prevents race conditions.
        reaction, created = PostReaction.objects.get_or_create(
            user=request.user, 
            post=post_obj,
            defaults={'status': 'L'}
        )
        
        # Case A: User has never reacted to this post before (New Record)
        if created:
            post_obj.like_count = F('like_count') + 1
            post_obj.save(update_fields=['like_count'])
            return Response({"message": "Liked", "status": "L"}, status=status.HTTP_200_OK)
            
        # Case B: User already has a reaction record in the database
        else:
            if reaction.status == 'L':
                # B1: Currently 'Liked'. User wants to 'Unlike' it.
                reaction.status = 'U'
                reaction.save(update_fields=['status'])
                
                # Atomically decrement the like count
                post_obj.like_count = F('like_count') - 1
                post_obj.save(update_fields=['like_count'])
                return Response({"message": "Unliked", "status": "U"}, status=status.HTTP_200_OK)
                
            else:
                # B2: Currently 'Unliked' ('U'). User wants to 'Like' it again.
                reaction.status = 'L'
                reaction.save(update_fields=['status'])
                
                # Atomically increment the like count
                post_obj.like_count = F('like_count') + 1
                post_obj.save(update_fields=['like_count'])
                return Response({"message": "Liked", "status": "L"}, status=status.HTTP_200_OK)

class StudentUpdateDeletePostAPIView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    serializer_class = PostUpdateSerializer
    lookup_field = "id"
    lookup_url_kwarg = "post_id"

    def get_queryset(self):
        return Post.objects.select_related("productive_test_history__student").all()

    @extend_schema(
        summary="Retrieve a post",
        description="Retrieves the details of a specific post. Note: This endpoint expects the same authorization schema since it shares the IsOwner permission.",
        tags=["posts"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update a post (Not Allowed)",
        description="PUT method is not supported. Please use PATCH instead.",
        tags=["posts"],
        responses={
            405: OpenApiResponse(description="Method not allowed"),
        }
    )
    def put(self, request, *args, **kwargs):
        return Response(
            {"detail": "PUT method is not supported. Please use PATCH for updates."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @extend_schema(
        summary="Partially update a post",
        description=dedent("""\
            Allows a student to partially update (e.g., just the description) a post they own.
            
            ### Example Test Case (1.2)
            * **URL:** `/api/forums/posts-update-delete/1`
            * **Method:** `PATCH`
            * **Auth:** Bearer Token (e.g., Student 4 owning Post 1)
            * **Body:** `{"title": "Edited Title by Student 4"}`
            * **Result:** Returns `200 OK` and the post's title is updated.
        """),
        tags=["posts"],
        responses={
            200: OpenApiResponse(description="Successfully updated the post"),
            400: OpenApiResponse(description="Bad request"),
            403: OpenApiResponse(description="Forbidden (Not the owner)"),
            404: OpenApiResponse(description="Post not found"),
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a post",
        description=dedent("""\
            Allows a student to delete a post they own.
            
            ### Example Test Case (1.4)
            * **URL:** `/api/forums/posts-update-delete/1`
            * **Method:** `DELETE`
            * **Auth:** Bearer Token (e.g., Student 4 owning Post 1)
            * **Result:** Returns `204 No Content`. The post is permanently deleted.
        """),
        tags=["posts"],
        responses={
            204: OpenApiResponse(description="Successfully deleted the post"),
            403: OpenApiResponse(description="Forbidden (Not the owner)"),
            404: OpenApiResponse(description="Post not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
