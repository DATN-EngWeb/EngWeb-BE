from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework import permissions, status, serializers
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.db import transaction

from tests.models import Test, ReceptiveAnswer, ReceptivePart, ReceptiveQuestion
from tests.serializers.full_test import (
    ProductiveTestRetrieveSerializer,
    ProductiveTestUpdateSerializer,
    ReceptiveTestRetrieveSerializer,
    ReceptiveTestFullUpdateSerializer,
)
from tests.permissions import IsAdminOrOwner

from tests.utils.renumber import renumber_receptive_test
from tests.utils.scoring import calculate_scores


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
@extend_schema(
    methods=["PATCH"],
    summary="Cập nhật hoặc tạo mới nội dung đề Receptive Test",
    description=(
        "API này cập nhật một đề Receptive Test theo test_id, bao gồm tạo mới/cập nhật/xóa parts, questions, answers.\n\n"
        "Sử dụng 'action' trong nested objects để chỉ định create, update hoặc delete.\n\n"
        "- 'create': Tạo mới object (không cần 'id')\n"
        "- 'update': Cập nhật object đã tồn tại (cần 'id')\n"
        "- 'delete': Xóa object (cần 'id')\n\n"
        "total_score và score của part không được phép patch vì được tính tự động.\n\n"
        "Sau khi cập nhật, sẽ renumber lại order và question_number.\n\n"
        "Chỉ admin hoặc chủ sở hữu mới có quyền thực hiện.\n\n"
        "Chỉ cập nhật nếu type của đề là R."
    ),
    tags=["full-test"],
    request=ReceptiveTestFullUpdateSerializer,
    responses={
        200: ReceptiveTestRetrieveSerializer,
        400: OpenApiResponse(description="Bad request"),
        403: OpenApiResponse(
            description="Forbidden: Only admin or owner can update this test"
        ),
        404: OpenApiResponse(
            description="Test type is not Receptive (R) or does not exist test_id"
        ),
    },
)
class ReceptiveTestRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
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

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = ReceptiveTestFullUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Prevent non-admin from setting status to 'R'
        if (
            "status" in validated_data
            and validated_data["status"] == "R"
            and not request.user.is_staff
        ):
            raise serializers.ValidationError(
                {"status": "Only admin can set status to 'R' (Removed)."}
            )

        with transaction.atomic():
            # Update Test fields
            test_fields = [
                "title",
                "type",
                "level",
                "skill",
                "time",
                "description",
                "status",
            ]
            for field in test_fields:
                if field in validated_data:
                    setattr(instance, field, validated_data[field])
            instance.save()

            # Update ReceptiveTest fields
            receptive_test_data = validated_data.get("receptive_test", {})
            receptive_test = instance.receptive_test
            # total_score is not allowed to patch, it's calculated
            receptive_test.save()

            # Process parts
            parts_data = receptive_test_data.get("receptive_parts", [])
            for part_data in parts_data:
                action = part_data["action"]
                if action == "create":
                    part = ReceptivePart(receptive_test=receptive_test)
                    part_fields = [
                        "order",
                        "format",
                        "description",
                        "content",
                        "resources",
                    ]
                    for field in part_fields:
                        if field in part_data:
                            setattr(part, field, part_data[field])
                    part.save()
                elif action in ["update", "delete"]:
                    if "id" not in part_data:
                        raise serializers.ValidationError(
                            "id is required for update/delete actions on parts."
                        )
                    part_id = part_data["id"]
                    try:
                        part = ReceptivePart.objects.get(
                            id=part_id, receptive_test=receptive_test
                        )
                    except ReceptivePart.DoesNotExist:
                        raise serializers.ValidationError(
                            f"Part with id {part_id} does not exist."
                        )

                    if action == "delete":
                        part.delete()  # Cascade delete questions and answers
                        continue  # Skip processing questions for deleted part
                    elif action == "update":
                        part_fields = [
                            "order",
                            "format",
                            "description",
                            "content",
                            "resources",
                        ]
                        for field in part_fields:
                            if field in part_data:
                                setattr(part, field, part_data[field])
                        part.save()
                else:
                    raise serializers.ValidationError(
                        f"Invalid action '{action}' for part."
                    )

                # Process questions in this part (only if part was created or updated)
                questions_data = part_data.get("receptive_questions", [])
                for question_data in questions_data:
                    q_action = question_data["action"]
                    if q_action == "create":
                        question = ReceptiveQuestion(receptive_part=part)
                        q_fields = [
                            "question_number",
                            "content",
                            "explanation",
                            "score",
                            "resources",
                        ]
                        for field in q_fields:
                            if field in question_data:
                                setattr(question, field, question_data[field])
                        question.save()
                    elif q_action in ["update", "delete"]:
                        if "id" not in question_data:
                            raise serializers.ValidationError(
                                "id is required for update/delete actions on questions."
                            )
                        q_id = question_data["id"]
                        try:
                            question = ReceptiveQuestion.objects.get(
                                id=q_id, receptive_part=part
                            )
                        except ReceptiveQuestion.DoesNotExist:
                            raise serializers.ValidationError(
                                f"Question with id {q_id} does not exist in part {part.id}."
                            )

                        if q_action == "delete":
                            question.delete()  # Cascade delete answers
                            continue  # Skip processing answers for deleted question
                        elif q_action == "update":
                            q_fields = [
                                "question_number",
                                "content",
                                "explanation",
                                "score",
                                "resources",
                            ]
                            for field in q_fields:
                                if field in question_data:
                                    setattr(question, field, question_data[field])
                            question.save()
                    else:
                        raise serializers.ValidationError(
                            f"Invalid action '{q_action}' for question."
                        )

                    # Process answers in this question (only if question was created or updated)
                    answers_data = question_data.get("receptive_answers", [])
                    for answer_data in answers_data:
                        a_action = answer_data["action"]
                        if a_action == "create":
                            answer = ReceptiveAnswer(receptive_question=question)
                            a_fields = [
                                "option_label",
                                "answer_text",
                                "is_correct",
                                "resources",
                            ]
                            for field in a_fields:
                                if field in answer_data:
                                    setattr(answer, field, answer_data[field])
                            answer.save()
                        elif a_action in ["update", "delete"]:
                            if "id" not in answer_data:
                                raise serializers.ValidationError(
                                    "id is required for update/delete actions on answers."
                                )
                            a_id = answer_data["id"]
                            try:
                                answer = ReceptiveAnswer.objects.get(
                                    id=a_id, receptive_question=question
                                )
                            except ReceptiveAnswer.DoesNotExist:
                                raise serializers.ValidationError(
                                    f"Answer with id {a_id} does not exist in question {question.id}."
                                )

                            if a_action == "delete":
                                answer.delete()
                            elif a_action == "update":
                                a_fields = [
                                    "option_label",
                                    "answer_text",
                                    "is_correct",
                                    "resources",
                                ]
                                for field in a_fields:
                                    if field in answer_data:
                                        setattr(answer, field, answer_data[field])
                                answer.save()
                        else:
                            raise serializers.ValidationError(
                                f"Invalid action '{a_action}' for answer."
                            )

            # Renumber after updates/deletes
            renumber_receptive_test(receptive_test)

            # Recalculate scores after changes
            calculate_scores(receptive_test)

        # Refetch instance with updated related data
        instance = (
            self.get_queryset()
            .select_related("receptive_test")
            .prefetch_related(
                "receptive_test__receptive_parts__receptive_questions__receptive_answers"
            )
            .get(pk=instance.pk)
        )

        # Return updated data
        retrieve_serializer = ReceptiveTestRetrieveSerializer(instance)
        return Response(retrieve_serializer.data, status=status.HTTP_200_OK)


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
class ProductiveTestRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
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

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = ProductiveTestUpdateSerializer(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Prevent non-admin from setting status to 'R'
        if (
            "status" in validated_data
            and validated_data["status"] == "R"
            and not request.user.is_staff
        ):
            raise serializers.ValidationError(
                {"status": "Only admin can set status to 'R' (Removed)."}
            )

        # Update using serializer's update method
        updated_instance = serializer.update(instance, validated_data)

        # Refresh instance from DB
        updated_instance.refresh_from_db()

        # Return updated data
        retrieve_serializer = ProductiveTestRetrieveSerializer(updated_instance)
        return Response(retrieve_serializer.data, status=status.HTTP_200_OK)
