from django.db.models import Count
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from textwrap import dedent
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationListSerializer
from .permissions import IsOwner


class NotificationListAPIView(generics.ListAPIView):
    serializer_class = NotificationListSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="List notifications",
        description=dedent("""\
            Retrieves a paginated list of notifications for the authenticated user.
            Optionally filter by read status using the `is_read` query parameter.

            ### Filters
            * `is_read` (optional) — Pass `true`/`false` to filter read/unread notifications.

            ### Example Test Cases
            * **Get all notifications:** `GET /api/notifications/` → Returns `200 OK` with list of all user notifications.
            * **Get unread only:** `GET /api/notifications/?is_read=false` → Returns `200 OK` with unread notifications.
            * **Unauthenticated:** `GET /api/notifications/` → Returns `401 Unauthorized`.
        """),
        tags=["notifications"],
        parameters=[
            OpenApiParameter(
                name="is_read",
                description="Filter notifications by read status (`true` or `false`).",
                required=False,
                type=bool,
            ),
        ],
        responses={
            200: NotificationListSerializer(many=True),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)

        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            is_read_val = is_read.lower() in ("true", "1", "yes")
            queryset = queryset.filter(is_read=is_read_val)

        return queryset

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class NotificationMarkReadAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    @extend_schema(
        summary="Mark a notification as read",
        description=dedent("""\
            Marks a specific notification as read by its ID.
            Only the owner of the notification can mark it as read.

            ### Example Test Cases
            * **Mark as read:** `PATCH /api/notifications/1/mark-read/` → Returns `200 OK` with updated notification.
            * **Not found:** `PATCH /api/notifications/999/mark-read/` → Returns `404 Not Found`.
            * **Not owner:** `PATCH /api/notifications/1/mark-read/` by another user → Returns `403 Forbidden`.
            * **Unauthenticated:** `PATCH /api/notifications/1/mark-read/` → Returns `401 Unauthorized`.
        """),
        tags=["notifications"],
        request=None,
        responses={
            200: NotificationListSerializer,
            401: OpenApiResponse(description="Authentication credentials were not provided."),
            403: OpenApiResponse(description="You do not have permission to access this notification."),
            404: OpenApiResponse(description="Notification not found."),
        },
    )
    def patch(self, request, pk):
        try:
            notification = self.get_queryset().get(pk=pk)
        except Notification.DoesNotExist:
            return Response(
                {"detail": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        notification.is_read = True
        notification.save(update_fields=["is_read"])

        return Response(
            NotificationListSerializer(notification, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationMarkAllReadAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Mark all notifications as read",
        description=dedent("""\
            Marks all unread notifications of the authenticated user as read.
            Returns the count of updated notifications.

            ### Example Test Cases
            * **Mark all as read:** `PATCH /api/notifications/mark-all-read/` → Returns `200 OK` with `{"message": "All notifications marked as read.", "updated_count": 5}`.
            * **No unread:** `PATCH /api/notifications/mark-all-read/` when all are read → Returns `200 OK` with `updated_count: 0`.
            * **Unauthenticated:** `PATCH /api/notifications/mark-all-read/` → Returns `401 Unauthorized`.
        """),
        tags=["notifications"],
        request=None,
        responses={
            200: OpenApiResponse(description="All notifications marked as read."),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
        },
    )
    def patch(self, request):
        updated = Notification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)

        return Response(
            {"message": "All notifications marked as read.", "updated_count": updated},
            status=status.HTTP_200_OK,
        )


class NotificationUnreadCountAPIView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get unread notification count",
        description=dedent("""\
            Returns the total number of unread notifications for the authenticated user.
            Designed to be called on login or page load to display a badge count.

            ### Example Test Cases
            * **Has unread:** `GET /api/notifications/unread-count/` → Returns `200 OK` with `{"unread_count": 3}`.
            * **None unread:** `GET /api/notifications/unread-count/` → Returns `200 OK` with `{"unread_count": 0}`.
            * **Unauthenticated:** `GET /api/notifications/unread-count/` → Returns `401 Unauthorized`.
        """),
        tags=["notifications"],
        responses={
            200: OpenApiResponse(description="Unread notification count retrieved."),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
        },
    )
    def get(self, request):
        count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()

        return Response({"unread_count": count}, status=status.HTTP_200_OK)
