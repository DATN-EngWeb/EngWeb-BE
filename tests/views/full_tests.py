from rest_framework.generics import RetrieveAPIView
from rest_framework import permissions
from drf_spectacular.utils import extend_schema, OpenApiResponse

from tests.models import Test
from tests.serializers.full_test import (
    ProductiveTestRetrieveSerializer,
    ReceptiveTestRetrieveSerializer,
)


@extend_schema(
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
            description="Test type is not Receptive (R) or does not exist test_id"
        ),
    },
)
class ReceptiveTestRetrieveAPIView(RetrieveAPIView):
    queryset = Test.objects.select_related("receptive_test").prefetch_related(
        "receptive_test__receptive_parts__receptive_questions__receptive_answers"
    )
    serializer_class = ReceptiveTestRetrieveSerializer
    lookup_field = "id"
    lookup_url_kwarg = "test_id"
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        if obj.type != "R":
            from rest_framework.exceptions import NotFound

            raise NotFound("This test is not Receptive Test (type is not R)")
        return obj


@extend_schema(
    summary="Lấy chi tiết đề Productive Test",
    description=(
        "API này trả về toàn bộ nội dung của một đề Productive Test (Speaking/Writing) theo test_id.\n\n"
        "Chỉ trả về nếu type của đề là P.\n\n"
    ),
    tags=["full-test"],
    responses={
        200: ProductiveTestRetrieveSerializer,
        404: OpenApiResponse(
            description="Test type is not Productive (P) or does not exist test_id"
        ),
    },
)
class ProductiveTestRetrieveAPIView(RetrieveAPIView):
    queryset = Test.objects.select_related("productive_test")
    serializer_class = ProductiveTestRetrieveSerializer
    lookup_field = "id"
    lookup_url_kwarg = "test_id"
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        if obj.type != "P":
            from rest_framework.exceptions import NotFound

            raise NotFound("This test is not Productive Test (type is not P)")
        return obj
