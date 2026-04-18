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
from rest_framework.exceptions import ValidationError

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

class UserRetrieveUpdateDeleteCommentAPIView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    serializer_class = PostCommentUpdateSerializer
    lookup_field = "id"
    lookup_url_kwarg = "comment_id"

    def get_queryset(self):
        return PostComment.objects.select_related("user").all()

    @extend_schema(
        summary="Retrieve a comment",
        description=dedent("""\
            Retrieves the details of a specific comment.

            ### Example Test Case (Success)
            * **URL:** `/api/forums/comments/10`
            * **Method:** `GET`
            * **Auth:** Bearer Token (Any authenticated user)
            * **Result:** Returns `200 OK` with the details of Comment ID 10 ("Thanks for sharing your work!").
        """),
        tags=["forum-comments"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update a comment (Not Allowed)",
        description="PUT method is not supported. Please use PATCH instead.",
        tags=["forum-comments"],
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
            
            ### Example Test Case (Success)
            * **URL:** `/api/forums/comments/10`
            * **Method:** `PATCH`
            * **Auth:** Bearer Token for `student4@example.com` (Owner of Comment 10)
            * **Body:** `{"content": "I changed my mind, this post is actually very awesome!"}`
            * **Result:** Returns `200 OK` and the comment's content is updated.
        """),
        tags=["forum-comments"],
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
            
            ### Example Test Case (Success)
            * **URL:** `/api/forums/comments/10`
            * **Method:** `DELETE`
            * **Auth:** Bearer Token for `student4@example.com` (Owner of Comment 10)
            * **Result:** Returns `204 No Content`. The comment is deleted and the parent post's `comment_count` decreases by 1. If another user (like student5) attempts this, it returns `403 Forbidden`.
        """),
        tags=["forum-comments"],
        responses={
            204: OpenApiResponse(description="Successfully deleted the comment"),
            403: OpenApiResponse(description="Forbidden (Not the owner)"),
            404: OpenApiResponse(description="Comment not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def perform_destroy(self, instance):
        post = instance.post
        comment_id = instance.id

        super().perform_destroy(instance)

        post.comment_count = F('comment_count') - 1
        post.save(update_fields=['comment_count'])

class ForumPagination(PageNumberPagination):
    page_size = 2
    page_size_query_param = "page_size"
    max_page_size = 10

class PostListCreateAPIView(generics.ListCreateAPIView):
    authentication_classes = [CustomTokenAuthentication]
    pagination_class = ForumPagination
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title"]
    ordering_fields = ["created_at", "like_count", "comment_count"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsOwner()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PostCreateSerializer
        return PostListSerializer

    def get_queryset(self):
        # We only need the complex queryset for GET requests
        if self.request.method != "GET":
            return Post.objects.all()
            
        test_id = self.request.query_params.get("test_id")
        if not test_id:
            raise ValidationError({"test_id": "This query parameter is required."})
            
        queryset = Post.objects.select_related(
            "productive_test_history",
            "productive_test_history__student__user",
            "productive_test_history__productive_test__test"
        )
        
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
        summary="Create a new forum post",
        description=dedent("""\
            Allows a student to share their submitted productive test (Writing or Speaking) to the forum. Must be authenticated and verified.

            ### Test Cases & Examples

            **1. Successful Post Creation**
            * **Method:** `POST`
            * **Body:** `{"productive_test_history_id": 1, "title": "My Writing Task", "description": "Please give me feedback!"}`
            * **Auth:** Bearer Token (Student who owns history_id=1)
            * **Result:** `201 Created`

            **2. Unauthorized Access (Sharing another student's test)**
            * **Method:** `POST`
            * **Body:** `{"productive_test_history_id": 2, "title": "Hacking your post"}`
            * **Auth:** Bearer Token (Student who does NOT own history_id=2)
            * **Result:** `403 Forbidden` (`"You can only share your own test histories."`)

            **3. Duplicate Post Prevention**
            * **Method:** `POST`
            * **Body:** Same as Case 1, but sent a second time.
            * **Result:** `400 Bad Request` (`"A post already exists for this test submission."`)
        """),
        tags=["forum-posts"],
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

    @extend_schema(
        summary="List forum posts",
        tags=["forum-posts"],
        description=dedent("""\
            Retrieves a paginated list of forum posts shared for a particular test. 
            Returns additional `is_liked` metadata for authenticated viewers.

            ### Test Cases & Examples (Based on System Seeds)
            Note: The database contains test posts for ProductiveTest ID 3 and 4. `student4@example.com` and `student5@example.com` (password123) own these posts.

            **1. Get all posts for a test (Authenticated)**
            * **URL:** `/api/forums/posts?test_id=3`
            * **Auth:** Bearer Token
            * **Result:** Returns 2 posts for the Writing test (ID=3). The most recent post (Post 2) appears first.

            **2. Filter by "Your Posts" tab**
            * **URL:** `/api/forums/posts?test_id=3&filter=mine`
            * **Auth:** Bearer Token (e.g., `student4@example.com`)
            * **Result:** Returns exactly 1 post (Post 1) authored by student4. Using student5's token returns Post 2.

            **3. Search by title/description**
            * **URL:** `/api/forums/posts?test_id=3&search=feedback`
            * **Auth:** Bearer Token
            * **Result:** Returns exactly 1 post (Post 2) containing the word "feedback".

            **4. Ordering (Most Liked)**
            * **URL:** `/api/forums/posts?test_id=3&ordering=-like_count`
            * **Auth:** Bearer Token
            * **Result:** Returns 2 posts, sorted by descending likes. Post 1 (11 likes) appears above Post 2 (8 likes).
        """),
        responses={
            200: OpenApiResponse(description="Successfully retrieved posts"),
            400: OpenApiResponse(description="Bad request, validation error"),
            401: OpenApiResponse(description="Unauthorized"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class PostCommentListCreateAPIView(generics.ListCreateAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ForumPagination
    
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at"]
    ordering = ["created_at"]
    
    def get_serializer_class(self):
        if self.request.method == "POST":
            return PostCommentCreateSerializer
        return PostCommentListSerializer

    def get_queryset(self):
        # We only need to filter for the GET list method
        if self.request.method != "GET":
            return PostComment.objects.all()
            
        post_id = self.request.query_params.get("post_id")
        if not post_id:
            raise ValidationError({"post_id": "This query parameter is required."})
            
        return PostComment.objects.select_related("user").filter(post_id=post_id)

    def perform_create(self, serializer):
        post = serializer.validated_data.get("post")
        comment = serializer.save(user=self.request.user)

        post.comment_count = F("comment_count") + 1
        post.save(update_fields=["comment_count"])

    @extend_schema(
        summary="Create a comment on a post",
        description=dedent("""\
            Allows any authenticated user to add a comment to a specific forum post.
            
            ### Example Test Case (Success)
            * **URL:** `/api/forums/comments`
            * **Method:** `POST`
            * **Auth:** Bearer Token (e.g., `student4@example.com`)
            * **Body:** `{"post_id": 1, "content": "This is a new test comment!"}`
            * **Result:** Returns `201 Created` and automatically updates the post's comment count safely.
            
            ### Example Test Case (Fail - Post Not Found)
            * **URL:** `/api/forums/comments`
            * **Method:** `POST`
            * **Auth:** Bearer Token
            * **Body:** `{"post_id": 999, "content": "Ghost comment"}`
            * **Result:** Returns `400 Bad Request` with `{"non_field_errors": ["Valid post not found."]}`.
        """),
        tags=["forum-comments"],
        responses={
            201: OpenApiResponse(description="Comment created successfully"),
            400: OpenApiResponse(description="Bad request, validation error"),
            404: OpenApiResponse(description="Post not found"),
        },
        examples=[
            OpenApiExample(
                "Successful comment",
                request_only=True,
                value={
                    "post_id": 1,
                    "content": "Great conclusion, but try to paraphrase the prompt more."
                }
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve comments for a specific post",
        tags=["forum-comments"],
        description=dedent("""\
            Retrieves a paginated list of comments for a given post, ordered oldest to newest by default.

            ### Test Cases & Examples (Based on System Seeds)
            Note: Post 1 initially has 10 seed comments in the DB.

            **1. Get comments list (Default)**
            * **URL:** `/api/forums/comments?post_id=1`
            * **Auth:** Bearer Token
            * **Result:** Returns comments for Post 1, ordered oldest to newest.

            **2. Reverse ordering (Newest first)**
            * **URL:** `/api/forums/comments?post_id=1&ordering=-created_at`
            * **Auth:** Bearer Token

            **3. Pagination (Custom page size)**
            * **URL:** `/api/forums/comments?post_id=1&page=2&page_size=5`
            * **Auth:** Bearer Token
            * **Result:** Skips the first 5 and returns comments 6 to 10.
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
        tags=["forum-reactions"],
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

class StudentRetrieveUpdateDeletePostAPIView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    serializer_class = PostUpdateSerializer
    lookup_field = "id"
    lookup_url_kwarg = "post_id"

    def get_queryset(self):
        return Post.objects.select_related("productive_test_history__student").all()

    @extend_schema(
        summary="Retrieve a post",
        description=dedent("""\
            Retrieves the details of a specific post. Note: This endpoint expects the same authorization schema since it shares the IsOwner permission.

            ### Example Test Case (Success)
            * **URL:** `/api/forums/posts/1`
            * **Method:** `GET`
            * **Auth:** Bearer Token (Any authenticated user)
            * **Result:** Returns `200 OK` with the details of Post ID 1 ("My first Writing Test - Environmental Issues").
        """),
        tags=["forum-posts"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update a post (Not Allowed)",
        description="PUT method is not supported. Please use PATCH instead.",
        tags=["forum-posts"],
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
            
            ### Example Test Case (Success)
            * **URL:** `/api/forums/posts/1`
            * **Method:** `PATCH`
            * **Auth:** Bearer Token for `student4@example.com` (Owner of Post 1)
            * **Body:** `{"title": "Edited Title by Student 4"}`
            * **Result:** Returns `200 OK` and the post's title is updated.
        """),
        tags=["forum-posts"],
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
            
            ### Example Test Case (Success)
            * **URL:** `/api/forums/posts/1`
            * **Method:** `DELETE`
            * **Auth:** Bearer Token for `student4@example.com` (Owner of Post 1)
            * **Result:** Returns `204 No Content`. The post is permanently deleted. If another user (like student5) attempts this, it returns `403 Forbidden`.
        """),
        tags=["forum-posts"],
        responses={
            204: OpenApiResponse(description="Successfully deleted the post"),
            403: OpenApiResponse(description="Forbidden (Not the owner)"),
            404: OpenApiResponse(description="Post not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
