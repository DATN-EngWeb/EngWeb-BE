from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
import django_filters

from feedback.models import TestFeedback
from forum.models import PostComment

from .serializers import (
    TeacherNotificationSerializer,
    StudentNotificationSerializer,
)
from .permissions import IsNotificationOwner
from .filters import NotificationFilter

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    inline_serializer,
)
from rest_framework import serializers
from textwrap import dedent


class NotificationPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 20


@extend_schema(
    methods=["GET"],
    summary="Get notification list",
    tags=["notifications"],
    description=dedent("""\
        Retrieves a paginated list of notifications for the authenticated user.

        ### Role-Based Notifications:
        - **Teacher**: Returns feedback comments from OTHER TEACHERS on tests created by this teacher.
          - Does NOT include AI-generated feedback (created_by="A").
          - Does NOT include feedback created by the teacher themselves.
        - **Student**: Returns comments from OTHER USERS on posts created by this student.
          - Does NOT include comments written by the student themselves.

        ### How to Test (Auth Required)
        1. Login (`POST /api/accounts/token`) with one of the following:
           - Teacher: `teacher10` / `admin`
           - Student: `student4` / `admin`
        2. Use the `access` token for Authorization header.

        ### Test Cases

        **1. Teacher - Successful Listing**
        * **URL:** `GET /api/notifications/read-all`
        * **Auth:** Bearer Token (e.g., `teacher10`)
        * **Result:** `200 OK` - Returns list of feedback from other teachers.
        * **Note:** If no feedback exists for teacher's tests, returns empty list.

        **2. Student - Successful Listing**
        * **URL:** `GET /api/notifications/read-all`
        * **Auth:** Bearer Token (e.g., `student4`)
        * **Result:** `200 OK` - Returns list of comments from other users on student's posts.
        * **Expected:** Based on seed data, `student4` has posts ID 1 and 3 with multiple comments.

        **3. Filter by Read Status (is_read=true)**
        * **URL:** `GET /api/notifications/read-all?is_read=true`
        * **Auth:** Bearer Token (any role)
        * **Result:** `200 OK` - Returns only notifications that have been read.

        **4. Filter by Read Status (is_read=false)**
        * **URL:** `GET /api/notifications/read-all?is_read=false`
        * **Auth:** Bearer Token (any role)
        * **Result:** `200 OK` - Returns only unread notifications.

        **5. Pagination**
        * **URL:** `GET /api/notifications/read-all?page=2&page_size=10`
        * **Auth:** Bearer Token (any role)
        * **Result:** `200 OK` - Returns second page with 10 items per page.
    """),
    parameters=[
        OpenApiParameter(
            name="is_read",
            type=bool,
            location=OpenApiParameter.QUERY,
            description="Filter notifications by read status (true/false)",
            required=False,
        ),
        OpenApiParameter(
            name="page",
            type=int,
            location=OpenApiParameter.QUERY,
            description="Page number for pagination",
            required=False,
        ),
        OpenApiParameter(
            name="page_size",
            type=int,
            location=OpenApiParameter.QUERY,
            description="Number of items per page (default: 5, max: 20)",
            required=False,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Successfully retrieved notifications",
            response=inline_serializer(
                name="NotificationListResponse",
                fields={
                    "count": serializers.IntegerField(),
                    "next": serializers.CharField(allow_null=True),
                    "previous": serializers.CharField(allow_null=True),
                    "results": inline_serializer(
                        name="NotificationResults",
                        many=True,
                        fields={
                            "id": serializers.IntegerField(),
                            "type": serializers.CharField(help_text="'F' for Teacher (TestFeedback), 'C' for Student (PostComment)"),
                            "test_id": serializers.IntegerField(help_text="Test ID (Both Teacher and Student)"),
                            "test_name": serializers.CharField(help_text="Test title (Teacher only)"),
                            "post_id": serializers.IntegerField(help_text="Post ID (Student only)"),
                            "post_title": serializers.CharField(help_text="Post title (Student only)"),
                            "skill": serializers.CharField(help_text="Skill type (e.g., 'Writing', 'Speaking')"),
                            "author": inline_serializer(
                                name="AuthorInfo",
                                fields={
                                    "name": serializers.CharField(),
                                    "avatar": serializers.CharField(allow_null=True),
                                },
                            ),
                            "message": serializers.CharField(help_text="Feedback comment or post comment content"),
                            "is_read": serializers.BooleanField(),
                            "created_at": serializers.DateTimeField(),
                        },
                    ),
                },
            ),
        ),
        401: OpenApiResponse(description="Unauthorized - Token missing or invalid"),
    },
)
class NotificationListAPIView(generics.ListAPIView):
    """
    GET /api/notifications/read-all
    Teacher: Get TestFeedback (only from other teachers) for tests created by this teacher
    Student: Get PostComment from other users for posts created by this student
    """
    permission_classes = []  # Handle permission based on role in get_queryset
    pagination_class = NotificationPagination
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = NotificationFilter

    def get_serializer_class(self):
        user = self.request.user
        if user.role == "T":
            return TeacherNotificationSerializer
        elif user.role == "S":
            return StudentNotificationSerializer
        return None

    def get_queryset(self):
        user = self.request.user

        if user.role == "T":
            # Teacher: Only get feedback from OTHER TEACHERS (created_by="T") for tests created by this teacher
            # Don't get feedback from AI (created_by="A")
            return TestFeedback.objects.filter(
                test__created_by__user=user,
                created_by="T"
            ).select_related(
                "test",
                "test__created_by",
                "test__created_by__user",
                "teacher",
                "teacher__user",
            ).order_by("-created_at")

        elif user.role == "S":
            # Student: Get comments from other users for posts created by this student
            # Remove comments from this student
            return PostComment.objects.filter(
                post__productive_test_history__student__user=user,
            ).exclude(
                user=user
            ).select_related(
                "post",
                "post__productive_test_history",
                "post__productive_test_history__productive_test",
                "post__productive_test_history__student__user",
                "user",
            ).order_by("-created_at")

        return TestFeedback.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.order_by("-created_at")
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

        if page is not None:
            return self.get_paginated_response(data)

        return Response(data, status=status.HTTP_200_OK)


@extend_schema(
    methods=["PATCH"],
    summary="Mark a notification as read",
    tags=["notifications"],
    description=dedent("""\
        Marks a specific notification as read.

        ### Role-Based Behavior:
        - **Teacher**: Marks a TestFeedback as read. The feedback must belong to a test created by this teacher.
        - **Student**: Marks a PostComment as read. The comment must belong to a post created by this student.

        ### How to Test (Auth Required)
        1. Login (`POST /api/accounts/token`) with one of the following:
           - Teacher: `teacher10` / `admin`
           - Student: `student4` / `admin`
        2. Use the `access` token for Authorization header.

        ### Test Cases

        **1. Successful Mark as Read**
        * **URL:** `PATCH /api/notifications/mark-read/<id>`
        * **Auth:** Bearer Token
        * **Result:** `200 OK` with `{"detail": "Marked as read."}`

        **2. Not Found (Invalid ID)**
        * **URL:** `PATCH /api/notifications/mark-read/99999`
        * **Auth:** Bearer Token
        * **Result:** `404 Not Found` with `{"detail": "Not found."}`

        **3. Forbidden (Not Owner)**
        * **URL:** `PATCH /api/notifications/mark-read/<id>`
        * **Auth:** Bearer Token of a different user who doesn't own the notification
        * **Result:** `404 Not Found` (returns 404 to hide resource existence)

        **4. Student Mark Read on Comment**
        * **URL:** `PATCH /api/notifications/mark-read/<comment_id>`
        * **Auth:** Bearer Token (e.g., `student4`)
        * **Result:** `200 OK` - The comment is marked as read.
    """),
    responses={
        200: OpenApiResponse(
            description="Notification marked as read successfully",
            response=inline_serializer(
                name="MarkReadSuccess",
                fields={
                    "detail": serializers.CharField(),
                },
            ),
        ),
        404: OpenApiResponse(description="Notification not found or not owned by user"),
        401: OpenApiResponse(description="Unauthorized - Token missing or invalid"),
    },
)
class NotificationMarkReadAPIView(generics.UpdateAPIView):
    """
    PATCH /api/notifications/<id>/mark-read
    Mark a notification as read (no need for type param because it's determined by role)
    """
    permission_classes = []  # Handle permission based on role in get_object

    def get_serializer_class(self):
        from .serializers import TeacherNotificationSerializer, StudentNotificationSerializer
        user = self.request.user
        if user.role == "T":
            return TeacherNotificationSerializer
        return StudentNotificationSerializer

    def get_queryset(self):
        user = self.request.user

        if user.role == "T":
            return TestFeedback.objects.filter(
                test__created_by__user=user,
                created_by="T"
            ).select_related(
                "test",
                "test__created_by",
                "test__created_by__user",
                "teacher",
                "teacher__user",
            )
        elif user.role == "S":
            return PostComment.objects.filter(
                post__productive_test_history__student__user=user
            ).exclude(
                user=user
            ).select_related(
                "post",
                "post__productive_test_history",
                "post__productive_test_history__productive_test",
                "post__productive_test_history__student__user",
                "user",
            )

        return TestFeedback.objects.none()

    def patch(self, request, *args, **kwargs):
        user = request.user
        notification_id = kwargs.get("id")

        if user.role == "T":
            # Teacher: Only mark-read TestFeedback
            try:
                feedback = TestFeedback.objects.get(pk=notification_id)
                # Verify ownership
                if user != feedback.test.created_by.user:
                    return Response(
                        {"detail": "Not found."},
                        status=status.HTTP_404_NOT_FOUND
                    )
                feedback.is_read = True
                feedback.save(update_fields=["is_read"])
                return Response({"detail": "Marked as read."})
            except TestFeedback.DoesNotExist:
                return Response(
                    {"detail": "Not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

        elif user.role == "S":
            # Student: Only mark-read PostComment
            try:
                comment = PostComment.objects.get(pk=notification_id)
                # Verify ownership
                if user != comment.post.productive_test_history.student.user:
                    return Response(
                        {"detail": "Not found."},
                        status=status.HTTP_404_NOT_FOUND
                    )
                comment.is_read = True
                comment.save(update_fields=["is_read"])
                return Response({"detail": "Marked as read."})
            except PostComment.DoesNotExist:
                return Response(
                    {"detail": "Not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

        return Response(
            {"detail": "Invalid request."},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    methods=["PATCH"],
    summary="Mark all notifications as read",
    tags=["notifications"],
    description=dedent("""\
        Marks all unread notifications as read for the authenticated user.

        ### Role-Based Behavior:
        - **Teacher**: Marks all unread feedback (from other teachers) as read.
        - **Student**: Marks all unread comments (from other users) as read.

        ### How to Test (Auth Required)
        1. Login (`POST /api/accounts/token`) with one of the following:
           - Teacher: `teacher10` / `admin`
           - Student: `student4` / `admin`
        2. Use the `access` token for Authorization header.

        ### Test Cases

        **1. Successful Mark All as Read**
        * **URL:** `PATCH /api/notifications/mark-all-read`
        * **Auth:** Bearer Token
        * **Result:** `200 OK` with `{"detail": "All notifications marked as read."}`

        **2. No Unread Notifications**
        * **URL:** `PATCH /api/notifications/mark-all-read`
        * **Auth:** Bearer Token (user with no unread notifications)
        * **Result:** `200 OK` - Updates 0 records, returns success message.
    """),
    responses={
        200: OpenApiResponse(
            description="All notifications marked as read successfully",
            response=inline_serializer(
                name="MarkAllReadSuccess",
                fields={
                    "detail": serializers.CharField(),
                },
            ),
        ),
        401: OpenApiResponse(description="Unauthorized - Token missing or invalid"),
    },
)
class NotificationMarkAllReadAPIView(APIView):
    """
    PATCH /api/notifications/mark-all-read
    Mark all notifications as read
    """

    def patch(self, request):
        user = request.user

        if user.role == "T":
            TestFeedback.objects.filter(
                test__created_by__user=user,
                created_by="T",
                is_read=False
            ).update(is_read=True)

        elif user.role == "S":
            PostComment.objects.filter(
                post__productive_test_history__student__user=user,
                is_read=False
            ).exclude(user=user).update(is_read=True)

        return Response({"detail": "All notifications marked as read."})


@extend_schema(
    methods=["GET"],
    summary="Get unread notification count",
    tags=["notifications"],
    description=dedent("""\
        Returns the total count of unread notifications for the authenticated user.

        ### Role-Based Behavior:
        - **Teacher**: Returns count of unread feedback from other teachers.
        - **Student**: Returns count of unread comments from other users.

        ### How to Test (Auth Required)
        1. Login (`POST /api/accounts/token`) with one of the following:
           - Teacher: `teacher10` / `admin`
           - Student: `student4` / `admin`
        2. Use the `access` token for Authorization header.

        ### Test Cases

        **1. Teacher - Get Unread Count**
        * **URL:** `GET /api/notifications/unread-count`
        * **Auth:** Bearer Token (e.g., `teacher10`)
        * **Result:** `200 OK` with `{"unread_count": <number>}`

        **2. Student - Get Unread Count**
        * **URL:** `GET /api/notifications/unread-count`
        * **Auth:** Bearer Token (e.g., `student4`)
        * **Result:** `200 OK` with `{"unread_count": <number>}`
        * **Expected:** Based on seed data, `student4` has 19 unread comments across posts 1 and 3.

        **3. Zero Unread Notifications**
        * **URL:** `GET /api/notifications/unread-count`
        * **Auth:** Bearer Token (fresh user with no notifications)
        * **Result:** `200 OK` with `{"unread_count": 0}`
    """),
    responses={
        200: OpenApiResponse(
            description="Unread count retrieved successfully",
            response=inline_serializer(
                name="UnreadCountResponse",
                fields={
                    "unread_count": serializers.IntegerField(),
                },
            ),
        ),
        401: OpenApiResponse(description="Unauthorized - Token missing or invalid"),
    },
)
class NotificationUnreadCountAPIView(APIView):
    """
    GET /api/notifications/unread-count
    Count the number of unread notifications
    """

    def get(self, request):
        user = request.user
        count = 0

        if user.role == "T":
            count = TestFeedback.objects.filter(
                test__created_by__user=user,
                created_by="T",
                is_read=False
            ).count()

        elif user.role == "S":
            count = PostComment.objects.filter(
                post__productive_test_history__student__user=user,
                is_read=False
            ).exclude(user=user).count()

        return Response({"unread_count": count})
