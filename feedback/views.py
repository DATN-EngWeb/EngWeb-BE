from accounts.authentication import CustomTokenAuthentication
from accounts.models import Student
from test_histories.models import ProductiveTestHistory
from tests.models import WritingCriteriaTemplate
from .utils import (
    build_ai_prompt_text,
    build_vertex_parts,
    deduct_ai_turn,
    extract_model_text,
    format_writing_criteria_text,
    load_prompt_html,
    parse_feedback_json,
    process_prompt_html_images,
)

from django.conf import settings
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)

from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

import vertexai
from vertexai.generative_models import GenerativeModel

@method_decorator(
    ratelimit(key="user", rate="5/m", method=["POST"], block=False),
    name="dispatch",
)
class AIFeedbackForWritingAPIView(generics.GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Generate AI feedback for writing",
        description=(
            "Validate request, process prompt/images, call Vertex AI (Gemini), store feedback, and deduct AI turns.\n\n"
            "**Flow:**\n"
            "1. Authenticate as a student (role `S`) and ensure the submission belongs to the current student.\n"
            "2. Load the productive writing test prompt (HTML + base64 images) and convert it to multimodal input.\n"
            "3. Build a detailed evaluation prompt using the writing criteria for the test level.\n"
            "4. Call Vertex AI Gemini with text + images and parse the JSON feedback.\n"
            "5. Atomically deduct 1 AI turn from `weekly_ai_turn` or `bonus_ai_turn`.\n\n"
            "**Seed examples for testing (using `productive_test_history_id`):**\n"
            "- Login as `student4` (user_id=1009, verified student). Call the history listing/detail API to obtain the `productive_test_history_id` row seeded for `student_id=1009`, `productive_test_id=3`, `type='S'`.\n"
            "- Login as `student5` (user_id=1010, verified student). Similarly, obtain the `productive_test_history_id` row seeded for `student_id=1010`, `productive_test_id=3`, `type='S'`.\n\n"
            "The actual `productive_test_history_id` values depend on your database state; always pass the primary key `productive_test_history_id` to this endpoint, not (`productive_test_id`, `attempt`)."
        ),
        tags=["feedback"],
        request=inline_serializer(
            name="AIFeedbackForWritingRequest",
            fields={
                "productive_test_history_id": serializers.IntegerField(required=True),
            },
        ),
        responses={
            200: OpenApiResponse(description="AI feedback generated successfully"),
            400: OpenApiResponse(description="Invalid request or no AI turns left"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="History not found"),
            502: OpenApiResponse(description="AI service error"),
        },
        examples=[
            OpenApiExample(
                name="Student4 - sample writing history",
                request_only=True,
                value={
                    "productive_test_history_id": 1,
                },
            ),
            OpenApiExample(
                name="Student5 - sample writing history",
                request_only=True,
                value={
                    "productive_test_history_id": 2,
                },
            ),
        ],
    )
    def post(self, request):
        # Rate limit protection to avoid abuse and reduce 429 from Vertex AI.
        if getattr(request, "limited", False):
            return Response(
                {
                    "detail": "Too many AI feedback requests. Please wait a few seconds before trying again."
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        history_id = request.data.get("productive_test_history_id")
        
        if not history_id:
            return Response(
                {"detail": "productive_test_history_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.user.role != "S":
            return Response(
                {"detail": "Only students can request AI writing feedback."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response(
                {"detail": "Student profile not found."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            history = ProductiveTestHistory.objects.select_related(
                "student__user",
                "productive_test__test",
            ).get(pk=history_id)
        except ProductiveTestHistory.DoesNotExist:
            return Response(
                {"detail": "Productive test history not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if history.student_id != student.pk:
            return Response(
                {"detail": "You can only request feedback for your own submission."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if history.type != "S":
            return Response(
                {"detail": "AI feedback is only available for submitted writing tests."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        test = history.productive_test.test

        if test.type != "P" or test.skill != "W":
            return Response(
                {"detail": "This endpoint only supports writing productive tests."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_answer = (history.user_answer_text or "").strip()

        if not user_answer:
            return Response(
                {"detail": "Submission has no writing answer text to evaluate."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if student.weekly_ai_turn <= 0 and student.bonus_ai_turn <= 0:
            return Response(
                {
                    "detail": "You have no AI feedback turns left. Please earn more to continue.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        prompt_html_content, _ = load_prompt_html(history.productive_test.description)
        processed_prompt_html, prompt_images = process_prompt_html_images(prompt_html_content)
        writing_criteria_rows = list(
            WritingCriteriaTemplate.objects.filter(level=test.level)
            .order_by("band")
            .values(
                "id",
                "level",
                "band",
                "content",
                "communicative_achievement",
                "organisation",
                "language",
            )
        )
        writing_criteria_text = format_writing_criteria_text(writing_criteria_rows)
        ai_prompt_text = build_ai_prompt_text(
            productive_test_format=history.productive_test.get_format_display(),
            test_level=test.level,
            processed_html_str=processed_prompt_html,
            writing_criteria_text=writing_criteria_text,
            student_answer_text=user_answer,
        )

        usage_data = None
        parsed_feedback = None

        try:
            vertexai.init(
                project=settings.VERTEX_AI_PROJECT_ID,
                location=settings.VERTEX_AI_LOCATION,
            )
            model = GenerativeModel(settings.VERTEX_AI_MODEL)
            parts = build_vertex_parts(ai_prompt_text, prompt_images)
            generation_config = {
                "temperature": settings.VERTEX_AI_TEMPERATURE,
            }
            model_response = model.generate_content(
                parts,
                generation_config=generation_config,
            )
            usage = getattr(model_response, "usage_metadata", None)

            if usage is not None:
                usage_data = {
                    "prompt_token_count": getattr(usage, "prompt_token_count", None),
                    "candidates_token_count": getattr(
                        usage, "candidates_token_count", None
                    ),
                    "total_token_count": getattr(usage, "total_token_count", None),
                }
                print(usage_data)

            feedback_text = extract_model_text(model_response)
            parsed_feedback = parse_feedback_json(feedback_text)
        except Exception as exc:
            return Response(
                {
                    "detail": "Failed to generate AI feedback at the moment.",
                    "error": f"{type(exc).__name__}: {exc}",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not feedback_text:
            return Response(
                {"detail": "AI returned empty feedback. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        deducted_student, turn_source_used = deduct_ai_turn(student.pk)
        
        if not deducted_student:
            return Response(
                {
                    "detail": "You have no AI feedback turns left. Please earn more to continue.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        history.ai_feedback = feedback_text
        history.save(update_fields=["ai_feedback"])

        return Response(
            {
                "message": "AI feedback generated successfully.",
                "productive_test_history_id": history.id,
                "ai_feedback": parsed_feedback if parsed_feedback is not None else feedback_text,
                "turn_source_used": turn_source_used,
                "remaining_turns": {
                    "weekly_ai_turn": deducted_student.weekly_ai_turn,
                    "bonus_ai_turn": deducted_student.bonus_ai_turn,
                },
            },
            status=status.HTTP_200_OK,
        )
