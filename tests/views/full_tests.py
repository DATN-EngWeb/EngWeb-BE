from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema, OpenApiResponse

from tests.models import Test
from tests.serializers.full_test import (
    ProductiveTestRetrieveSerializer,
    ProductiveTestUpdateSerializer,
    ReceptiveTestRetrieveSerializer,
)
from tests.permissions import IsAdminOrOwner


@extend_schema(
    methods=["GET"],
    summary="Lấy chi tiết đề Receptive Test",
    description=(
        "API này trả về toàn bộ nội dung của một đề Receptive Test (Reading/Listening) theo test_id.\n\n"
        "Chỉ trả về nếu type của đề là R.\n\n"
        "Response bao gồm thông tin đề, các phần, câu hỏi và đáp án."
    ),
    tags=["full-test"],
    responses={
        200: ReceptiveTestRetrieveSerializer,
        404: OpenApiResponse(
            description="Test type is not Receptive (R), does not exist, or has been removed (for non-admin users)"
        ),
    },
)
@extend_schema(
    methods=["DELETE"],
    summary="Soft delete đề Receptive Test",
    description=(
        "API này thực hiện soft delete một đề Receptive Test theo test_id bằng cách cập nhật status thành 'R'.\n\n"
        "Chỉ admin hoặc chủ sở hữu mới có quyền thực hiện.\n\n"
        "Chỉ áp dụng nếu type của đề là R."
    ),
    tags=["full-test"],
    responses={
        200: OpenApiResponse(
            description="Test has been soft deleted successfully (status=R) or Test is already soft deleted."
        ),
        403: OpenApiResponse(
            description="Forbidden: Only admin or owner can delete this test"
        ),
        404: OpenApiResponse(
            description="Test type is not Receptive (R) or does not exist test_id"
        ),
    },
)
@extend_schema(methods=["PUT"], exclude=True)
class ReceptiveTestRetrieveAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Test.objects.select_related("receptive_test").prefetch_related(
        "receptive_test__receptive_parts__receptive_questions__receptive_answers"
    )
    serializer_class = ReceptiveTestRetrieveSerializer
    lookup_field = "id"
    lookup_url_kwarg = "test_id"
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [permissions.IsAuthenticated(), IsAdminOrOwner()]
        return [permissions.IsAuthenticated()]

    def get_object(self):
        obj = super().get_object()
        if obj.type != "R":
            raise NotFound("This test is not Receptive Test (type is not R)")
        if not self.request.user.is_staff and obj.status == "R":
            raise NotFound("This test has been removed.")
        return obj

    def put(self, request, *args, **kwargs):
        return Response(
            {"detail": "PUT method is not allowed. Use PATCH instead."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status == "R":
            return Response(
                {"detail": "Test is already soft deleted."},
                status=status.HTTP_200_OK,
            )
        instance.status = "R"  # Soft delete by setting status to Removed
        instance.save()
        return Response(
            {
                "detail": f"Test has been soft deleted successfully (status={instance.status})."
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    methods=["GET"],
    summary="Lấy chi tiết đề Productive Test",
    description=(
        "API này trả về toàn bộ nội dung của một đề Productive Test (Speaking/Writing) theo test_id.\n\n"
        "Chỉ trả về nếu type của đề là P.\n\n"
    ),
    tags=["full-test"],
    responses={
        200: ProductiveTestRetrieveSerializer,
        404: OpenApiResponse(
            description="Test type is not Productive (P), does not exist, or has been removed (for non-admin users)"
        ),
    },
)
@extend_schema(
    methods=["PATCH"],
    summary="Cập nhật đề Productive Test",
    description=(
        "API này cập nhật một đề Productive Test theo test_id.\n\n"
        "Chỉ admin hoặc chủ sở hữu mới có quyền cập nhật.\n\n"
        "Chỉ cập nhật nếu type của đề là P."
    ),
    tags=["full-test"],
    request=ProductiveTestUpdateSerializer,
    responses={
        200: ProductiveTestRetrieveSerializer,
        400: OpenApiResponse(description="Bad request"),
        403: OpenApiResponse(
            description="Forbidden: Only admin or owner can update this test"
        ),
        404: OpenApiResponse(
            description="Test type is not Productive (P) or does not exist test_id"
        ),
    },
)
@extend_schema(
    methods=["DELETE"],
    summary="Soft delete đề Productive Test",
    description=(
        "API này thực hiện soft delete một đề Productive Test theo test_id bằng cách cập nhật status thành 'R'.\n\n"
        "Chỉ admin hoặc chủ sở hữu mới có quyền thực hiện.\n\n"
        "Chỉ áp dụng nếu type của đề là P."
    ),
    tags=["full-test"],
    responses={
        200: OpenApiResponse(
            description="Test has been soft deleted successfully (status=R) or Test is already soft deleted."
        ),
        403: OpenApiResponse(
            description="Forbidden: Only admin or owner can delete this test"
        ),
        404: OpenApiResponse(
            description="Test type is not Productive (P) or does not exist test_id"
        ),
    },
)
@extend_schema(methods=["PUT"], exclude=True)
class ProductiveTestRetrieveAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Test.objects.select_related("productive_test")
    serializer_class = ProductiveTestRetrieveSerializer
    lookup_field = "id"
    lookup_url_kwarg = "test_id"
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return ProductiveTestUpdateSerializer
        return ProductiveTestRetrieveSerializer

    def get_permissions(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return [permissions.IsAuthenticated(), IsAdminOrOwner()]
        return [permissions.IsAuthenticated()]

    def get_object(self):
        obj = super().get_object()
        if obj.type != "P":
            raise NotFound("This test is not Productive Test (type is not P)")
        if not self.request.user.is_staff and obj.status == "R":
            raise NotFound("This test has been removed.")
        return obj

    def put(self, request, *args, **kwargs):
        return Response(
            {"detail": "PUT method is not allowed. Use PATCH instead."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status == "R":
            return Response(
                {"detail": "Test is already soft deleted."},
                status=status.HTTP_200_OK,
            )
        instance.status = "R"  # Soft delete by setting status to Removed
        instance.save()
        return Response(
            {
                "detail": f"Test has been soft deleted successfully (status={instance.status})."
            },
            status=status.HTTP_200_OK,
        )
