from accounts.authentication import CustomTokenAuthentication
from accounts.models import Student, Teacher
from test_histories.models import ProductiveTestHistory
from tests.models import (
    ReadingCriteriaTemplate,
    SpeakingCriteriaTemplate,
    Test,
    WritingCriteriaTemplate,
)
from .utils import (
    build_ai_prompt_text,
    build_genai_parts_with_audio,
    build_genai_parts_with_images,
    build_genai_parts_with_pdf,
    deduct_ai_turn,
    extract_model_text,
    format_writing_criteria_text,
    generate_with_genai,
    load_prompt_html,
    parse_feedback_json,
    process_prompt_html_images,
)
from .models import TestFeedback
from .serializers import (
    TestFeedbackListSerializer, 
    TeacherTestFeedbackCreateSerializer,
    TeacherTestFeedbackUpdateSerializer,
)
from .permissions import IsTeacher

from django.conf import settings
from django.db import transaction
from django.db.models import Case, When, Value, IntegerField
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)

from rest_framework import generics, serializers, status, permissions
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied

from textwrap import dedent
from .filters import TestFeedbackFilterSet
from storage.utils.gcs_presigned import GCSPresignedURLManager


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
        processed_prompt_html, prompt_images = process_prompt_html_images(
            prompt_html_content
        )
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
            parts = build_genai_parts_with_images(ai_prompt_text, prompt_images)
            model_response = generate_with_genai(
                parts=parts,
                temperature=settings.VERTEX_AI_TEMPERATURE,
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

            feedback_text = extract_model_text(model_response)
            parsed_feedback = parse_feedback_json(feedback_text)

            if parsed_feedback is not None:
                if not isinstance(parsed_feedback, dict):
                    raise ValueError("AI feedback JSON must be an object.")

                revised_text = parsed_feedback.get("revised_text")
                if not isinstance(revised_text, str) or not revised_text.strip():
                    raise ValueError(
                        "AI feedback JSON is missing required plain-text field 'revised_text'."
                    )
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
                "ai_feedback": parsed_feedback
                if parsed_feedback is not None
                else feedback_text,
                "turn_source_used": turn_source_used,
                "remaining_turns": {
                    "weekly_ai_turn": deducted_student.weekly_ai_turn,
                    "bonus_ai_turn": deducted_student.bonus_ai_turn,
                },
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(
    ratelimit(key="user", rate="2/m", method=["POST"], block=False),
    name="dispatch",
)
class AIFeedbackForSpeakingAPIView(generics.GenericAPIView):
    """
    Generate AI feedback for speaking productive tests using Gemini with text + audio (GCS URI).
    """

    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Generate AI feedback for speaking",
        description=(
            "Validate request, load the speaking productive test and student's audio, call Vertex AI (Gemini) "
            "with text + audio, store feedback, and deduct AI turns.\n\n"
            "**Audio source:**\n"
            "- The student's audio is stored in `productive_test_history.audio_path` either as a GCS URI "
            "with the form `gs://bucket/path/to/file.webm` (or .wav/.mp3/.m4a) **or** as a public "
            "Google Cloud Storage URL starting with `https://storage.googleapis.com/`.\n"
            "- The backend will automatically convert URLs of the form "
            "`https://storage.googleapis.com/<bucket>/<object>` into the equivalent `gs://<bucket>/<object>` "
            "when calling Vertex AI.\n"
            "- This endpoint does **not** accept raw audio in the request body; it always reads from the history row.\n\n"
            "**Flow:**\n"
            "1. Authenticate as a student (role `S`) and ensure the history belongs to the current student.\n"
            "2. Ensure the test is a productive speaking test and that an audio path exists.\n"
            "3. Load the prompt/description and speaking criteria for the test level.\n"
            "4. Call Vertex AI Gemini with prompt text + audio and parse the JSON feedback into a structured object.\n"
            "5. Atomically deduct 1 AI turn from `weekly_ai_turn` or `bonus_ai_turn`.\n\n"
            "**Seed examples for testing (using `productive_test_history_id`):**\n"
            "- Login as `student4` (user_id=1009, verified student). Use the history listing/detail API to "
            "find the speaking history row seeded for `student_id=1009`, `productive_test_id=4`, `type='S'`, "
            "then pass its primary key `productive_test_history_id` to this endpoint.\n"
            "- Login as `student5` (user_id=1010, verified student). Similarly, use the history listing/detail API "
            "to find the speaking history row seeded for `student_id=1010`, `productive_test_id=4`, `type='S'`, "
            "and pass its primary key to this endpoint.\n\n"
            "The actual `productive_test_history_id` values depend on your database state; always pass the primary key, "
            "not (`productive_test_id`, `attempt`)."
        ),
        tags=["feedback"],
        request=inline_serializer(
            name="AIFeedbackForSpeakingRequest",
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
                name="Student4 - sample speaking history",
                request_only=True,
                value={
                    "productive_test_history_id": 3,
                },
            ),
            OpenApiExample(
                name="Student5 - sample speaking history",
                request_only=True,
                value={
                    "productive_test_history_id": 4,
                },
            ),
        ],
    )
    def post(self, request):
        if getattr(request, "limited", False):
            return Response(
                {
                    "detail": "Too many AI speaking feedback requests. Please wait a few seconds before trying again."
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
                {"detail": "Only students can request AI speaking feedback."},
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
                {"detail": "AI feedback is only available for submitted speaking tests."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        test = history.productive_test.test

        if test.type != "P" or test.skill != "S":
            return Response(
                {"detail": "This endpoint only supports speaking productive tests."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_audio_path = (history.audio_path or "").strip()

        if not raw_audio_path:
            return Response(
                {"detail": "Submission has no audio to evaluate."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Allow both gs:// and https://storage.googleapis.com/... and convert transparently to gs://
        if raw_audio_path.startswith("gs://"):
            audio_gcs_uri = raw_audio_path
        elif raw_audio_path.startswith("https://storage.googleapis.com/"):
            # https://storage.googleapis.com/<bucket>/<object> -> gs://<bucket>/<object>
            without_prefix = raw_audio_path[len("https://storage.googleapis.com/") :]
            # Split on first '/' to separate bucket and object path
            parts = without_prefix.split("/", 1)
            if len(parts) == 2 and parts[0] and parts[1]:
                audio_gcs_uri = f"gs://{parts[0]}/{parts[1]}"
            else:
                return Response(
                    {
                        "detail": "audio_path is not a valid GCS URL. Expected format "
                        "'https://storage.googleapis.com/<bucket>/<object>' or 'gs://<bucket>/<object>'."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {
                    "detail": "audio_path must be a GCS URI (starting with 'gs://') or a "
                    "Google Cloud Storage URL starting with 'https://storage.googleapis.com/'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if student.weekly_ai_turn <= 0 and student.bonus_ai_turn <= 0:
            return Response(
                {
                    "detail": "You have no AI feedback turns left. Please earn more to continue.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Load prompt/description text (can be raw HTML or plain text).
        prompt_text, _ = load_prompt_html(history.productive_test.description)
        prompt_text = (prompt_text or "").strip()

        # Build speaking criteria text
        speaking_rows = list(
            SpeakingCriteriaTemplate.objects.filter(level=test.level)
            .order_by("band")
            .values(
                "level",
                "band",
                "grammar_and_vocabulary",
                "discourse_management",
                "pronunciation",
                "task_achievement",
            )
        )

        if not speaking_rows:
            return Response(
                {"detail": "No speaking criteria template is available for this level."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        criteria_lines = []
        for row in speaking_rows:
            criteria_lines.append(
                "\n".join(
                    [
                        f"Band {row['band']} ({row['level']}):",
                        f"- Grammar and Vocabulary: {row['grammar_and_vocabulary'] or ''}",
                        f"- Discourse Management: {row['discourse_management'] or ''}",
                        f"- Pronunciation: {row['pronunciation'] or ''}",
                        f"- Task Achievement: {row['task_achievement'] or ''}",
                    ]
                )
            )
        speaking_criteria_text = "\n\n".join(criteria_lines)

        ai_prompt_text = (
            "You are an English speaking examiner.\n\n"
            f"I have a {history.productive_test.get_format_display()} speaking test at CEFR level {test.level}.\n\n"
            "The candidate's task is monologue-style (one-way speaking). There is no interactive communication with an examiner.\n\n"
            "Task description or prompt (may be HTML or plain text):\n"
            f"{prompt_text}\n\n"
            "Speaking scoring criteria:\n"
            f"{speaking_criteria_text}\n\n"
            "You are also given the student's recorded answer as an audio file.\n\n"
            "Instructions:\n"
            "1. Listen carefully to the full recording before scoring.\n"
            "2. Evaluate the performance against each criterion: Grammar and Vocabulary, Discourse Management, Pronunciation, Task Achievement.\n"
            "3. Produce a structured JSON object with EXACTLY the following shape:\n\n"
            "{\n"
            '  "grammar_and_vocabulary": {\n'
            '    "band": <integer from the given scale>,\n'
            '    "strengths": "<short paragraph about what the student does well>",\n'
            '    "improvements": "<short paragraph about what the student needs to improve>"\n'
            "  },\n"
            '  "discourse_management": {\n'
            '    "band": <integer>,\n'
            '    "strengths": "<short paragraph about coherence, cohesion and length of turns>",\n'
            '    "improvements": "<short paragraph about issues and how to fix them>"\n'
            "  },\n"
            '  "pronunciation": {\n'
            '    "band": <integer>,\n'
            '    "strengths": "<short paragraph describing intelligibility, stress and intonation>",\n'
            '    "improvements": "<short paragraph describing concrete pronunciation issues and tips>"\n'
            "  },\n"
            '  "task_achievement": {\n'
            '    "band": <integer>,\n'
            '    "strengths": "<short paragraph about how well the task is fulfilled (content, relevance, coverage of points)>",\n'
            '    "improvements": "<short paragraph about missing or weak parts of the task>"\n'
            "  },\n"
            '  "overall": {\n'
            '    "summary": "<3–5 sentences summarising the overall performance at CEFR level '
            f'{test.level}>",\n'
            '    "next_actions": "<2–4 specific things the student should do next to improve speaking>"\n'
            "  }\n"
            "}\n\n"
            "4. The value of each field must be plain text only (no nested JSON, no markdown syntax).\n"
            "5. CRITICAL: Return ONLY the raw JSON object. Do NOT wrap it in markdown code fences (```json ... ```). "
            "Do NOT add any prefix text like 'json' or 'Here is the JSON:'. Do NOT add any suffix text or explanations. "
            "Start your response directly with '{' and end with '}'.\n"
            "6. Do not explain the JSON, do not add any extra text before or after it. Return ONLY the JSON object.\n"
            "7. Do not end any sentence halfway; always complete your thoughts.\n"
            "8. Do not invent missing prompt details; rely only on the provided task description and audio.\n"
            "9. STRICT RULE: Always address the candidate directly as 'you' or 'your' (e.g., 'You pronounced words clearly', 'Your intonation needs work'). CRITICAL: NEVER use third-person pronouns like 'the student', 'he', 'she', or 'they' to refer to the candidate.\n"
        )

        # Infer MIME type from file extension (best-effort).
        lower_uri = audio_gcs_uri.lower()
        if lower_uri.endswith(".mp3"):
            audio_mime = "audio/mp3"
        elif lower_uri.endswith(".wav"):
            audio_mime = "audio/wav"
        elif lower_uri.endswith(".m4a"):
            audio_mime = "audio/m4a"
        else:
            audio_mime = "audio/wav"

        usage_data = None
        parsed_feedback = None

        try:
            parts = build_genai_parts_with_audio(
                ai_prompt_text=ai_prompt_text,
                audio_gcs_uri=audio_gcs_uri,
                mime_type=audio_mime,
            )
            model_response = generate_with_genai(
                parts=parts,
                temperature=settings.VERTEX_AI_TEMPERATURE,
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
                "ai_feedback": parsed_feedback
                if parsed_feedback is not None
                else feedback_text,
                "turn_source_used": turn_source_used,
                "remaining_turns": {
                    "weekly_ai_turn": deducted_student.weekly_ai_turn,
                    "bonus_ai_turn": deducted_student.bonus_ai_turn,
                },
                "usage": usage_data,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(
    ratelimit(key="user", rate="2/m", method=["POST"], block=False),
    name="dispatch",
)
class AIFeedbackForReadingAPIView(generics.GenericAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [IsTeacher]

    @extend_schema(
        summary="Generate AI feedback for reading test design",
        description=(
            "Generate AI review feedback for a teacher-created reading test using a PDF uploaded to GCS. "
            "The API validates teacher ownership, test status ('I' - In Review), AI turn availability, and "
            "GCS URI format before calling Vertex AI.\n\n"
            "Input must include `test_id` and `pdf_gcs_uri` (gs://bucket/tests/test_<id>/uuid-file.pdf). "
            "The uploaded PDF is always deleted after processing (success or failure)."
        ),
        tags=["feedback"],
        request=inline_serializer(
            name="AIFeedbackForReadingRequest",
            fields={
                "test_id": serializers.IntegerField(required=True),
                "pdf_gcs_uri": serializers.CharField(required=True),
            },
        ),
        responses={
            200: OpenApiResponse(description="AI reading feedback generated successfully"),
            400: OpenApiResponse(description="Invalid request or business rule violation"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Test not found"),
            502: OpenApiResponse(description="AI service error"),
        },
    )
    def post(self, request):
        if getattr(request, "limited", False):
            return Response(
                {
                    "detail": "Too many AI reading feedback requests. Please wait a bit before trying again."
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        test_id = request.data.get("test_id")
        pdf_gcs_uri = (request.data.get("pdf_gcs_uri") or "").strip()

        if not test_id:
            return Response(
                {"detail": "test_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not pdf_gcs_uri:
            return Response(
                {"detail": "pdf_gcs_uri is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not pdf_gcs_uri.startswith("gs://"):
            return Response(
                {"detail": "pdf_gcs_uri must start with 'gs://'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            teacher = Teacher.objects.select_related("user").get(user=request.user)
        except Teacher.DoesNotExist:
            return Response(
                {"detail": "Teacher profile not found."},
                status=status.HTTP_403_FORBIDDEN,
            )

        test = (
            Test.objects.select_related("created_by__user")
            .filter(pk=test_id, type="R", skill="R")
            .first()
        )
        if not test:
            self._cleanup_temp_pdf(pdf_gcs_uri)
            return Response(
                {"detail": "Reading test not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if test.status != "I":
            self._cleanup_temp_pdf(pdf_gcs_uri)
            return Response(
                {
                    "detail": "AI review is only allowed when the test status is 'In Review' (I)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not test.created_by_id or test.created_by_id != teacher.pk:
            self._cleanup_temp_pdf(pdf_gcs_uri)
            return Response(
                {"detail": "Only the teacher who created this test can request AI review."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if teacher.weekly_ai_turn <= 0:
            self._cleanup_temp_pdf(pdf_gcs_uri)
            return Response(
                {
                    "detail": "You have no AI review turns left. Please wait for the next weekly reset.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        uri_without_prefix = pdf_gcs_uri[len("gs://") :]
        uri_parts = uri_without_prefix.split("/", 1)
        if len(uri_parts) != 2 or not uri_parts[0] or not uri_parts[1]:
            self._cleanup_temp_pdf(pdf_gcs_uri)
            return Response(
                {
                    "detail": "Invalid pdf_gcs_uri format. Expected 'gs://<bucket>/<object>'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        bucket_name, object_key = uri_parts[0], uri_parts[1]
        if bucket_name != settings.GCS_BUCKET_NAME:
            self._cleanup_temp_pdf(pdf_gcs_uri)
            return Response(
                {"detail": "pdf_gcs_uri bucket is not allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expected_prefix = f"tests/test_{test.id}/"
        if not object_key.startswith(expected_prefix):
            self._cleanup_temp_pdf(pdf_gcs_uri)
            return Response(
                {
                    "detail": f"pdf_gcs_uri must point to an object under '{expected_prefix}'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not object_key.lower().endswith(".pdf"):
            self._cleanup_temp_pdf(pdf_gcs_uri)
            return Response(
                {"detail": "pdf_gcs_uri must reference a .pdf file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        gcs_manager = GCSPresignedURLManager()
        metadata = gcs_manager.get_object_metadata(object_key)
        if not metadata.get("exists"):
            return Response(
                {"detail": "Uploaded PDF was not found in GCS."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_size = metadata.get("size") or 0
        if file_size <= 0 or file_size > gcs_manager.MAX_FILE_SIZE:
            self._cleanup_temp_pdf(pdf_gcs_uri)
            return Response(
                {
                    "detail": f"PDF file size must be between 1 byte and {gcs_manager.MAX_FILE_SIZE} bytes.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        reading_criteria_rows = list(
            ReadingCriteriaTemplate.objects.filter(level=test.level)
            .order_by("priority")
            .values("code", "name", "description", "checkpoints", "priority")
        )

        if not reading_criteria_rows:
            self._cleanup_temp_pdf(pdf_gcs_uri)
            return Response(
                {"detail": "No reading criteria template available for this test level."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        criteria_blocks = []
        for row in reading_criteria_rows:
            checkpoints = row.get("checkpoints") or []
            if not isinstance(checkpoints, list):
                checkpoints = []
            checkpoint_lines = "\n".join([f"   - {item}" for item in checkpoints])
            criteria_blocks.append(
                "\n".join(
                    [
                        f"{row['priority']}. {row['name']} ({row['code']}):",
                        f"   Description: {row['description']}",
                        "   Checkpoints:",
                        checkpoint_lines if checkpoint_lines else "   - (No checkpoints)",
                    ]
                )
            )

        criteria_text = "\n\n".join(criteria_blocks)

        ai_prompt_text = (
            "You are a senior English reading-test design reviewer.\n\n"
            "You are given a teacher-created reading test as a PDF. Your task is to review the quality of test design, "
            "not to solve the test as a student.\n\n"
            f"Test metadata:\n- Title: {test.title}\n- CEFR Level: {test.level}\n\n"
            "Use the following rubric criteria:\n"
            f"{criteria_text}\n\n"
            "Output requirements (STRICT):\n"
            "1. Return ONLY valid HTML fragment in English (no markdown, no code fences).\n"
            "2. Do NOT include <html>, <head>, <body>, <style>, or <script>.\n"
            "3. Use only these tags: <h3>, <p>, <ul>, <ol>, <li>, <strong>, <em>.\n"
            "4. Structure your output in this order:\n"
            "   - <h3>Executive Summary</h3>\n"
            "   - <h3>Strengths</h3>\n"
            "   - <h3>High-Priority Issues</h3>\n"
            "   - <h3>Medium/Low-Priority Issues</h3>\n"
            "   - <h3>Recommended Revisions</h3>\n"
            "   - <h3>Final Verdict</h3>\n"
            "5. Make feedback concrete and actionable for a teacher who authored the test.\n"
            "6. If any part of the PDF is unclear or unreadable, explicitly state assumptions/uncertainties.\n"
            "7. Do not fabricate missing content.\n"
        )

        usage_data = None
        feedback_html = ""

        try:
            parts = build_genai_parts_with_pdf(
                ai_prompt_text=ai_prompt_text,
                pdf_gcs_uri=pdf_gcs_uri,
            )
            model_response = generate_with_genai(
                parts=parts,
                temperature=settings.VERTEX_AI_TEMPERATURE,
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

            feedback_html = extract_model_text(model_response)
        except Exception as exc:
            return Response(
                {
                    "detail": "Failed to generate AI reading feedback at the moment.",
                    "error": f"{type(exc).__name__}: {exc}",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        finally:
            # self._cleanup_temp_pdf(pdf_gcs_uri)
            print("not delete")

        if not feedback_html:
            return Response(
                {"detail": "AI returned empty feedback. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            with transaction.atomic():
                teacher_locked = Teacher.objects.select_for_update().get(pk=teacher.pk)
                if teacher_locked.weekly_ai_turn <= 0:
                    return Response(
                        {
                            "detail": "You have no AI review turns left. Please wait for the next weekly reset.",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                teacher_locked.weekly_ai_turn -= 1
                teacher_locked.save(update_fields=["weekly_ai_turn"])

                feedback_row, _created = TestFeedback.objects.update_or_create(
                    test_id=test.id,
                    created_by="A",
                    defaults={
                        "teacher": None,
                        "comment": feedback_html,
                    },
                )
        except Exception as exc:
            return Response(
                {
                    "detail": "Failed to persist AI reading feedback.",
                    "error": f"{type(exc).__name__}: {exc}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": "AI reading feedback generated successfully.",
                "test_id": test.id,
                "feedback_id": feedback_row.id,
                "ai_feedback": feedback_html,
                "remaining_turns": {
                    "weekly_ai_turn": teacher_locked.weekly_ai_turn,
                },
                "usage": usage_data,
            },
            status=status.HTTP_200_OK,
        )

    def _cleanup_temp_pdf(self, pdf_gcs_uri: str):
        if not pdf_gcs_uri or not pdf_gcs_uri.startswith("gs://"):
            return

        try:
            without_prefix = pdf_gcs_uri[len("gs://") :]
            parts = without_prefix.split("/", 1)
            if len(parts) != 2:
                return

            bucket, key = parts[0], parts[1]
            if bucket != settings.GCS_BUCKET_NAME or not key.startswith("tests/test_"):
                return

            gcs_manager = GCSPresignedURLManager()
            deleted = gcs_manager.delete_object(key)
            if not deleted:
                print(f"[AIFeedbackForReadingAPIView] Failed to delete uploaded PDF: {pdf_gcs_uri}")
        except Exception as exc:
            print(f"[AIFeedbackForReadingAPIView] Error deleting uploaded PDF {pdf_gcs_uri}: {exc}")


class FeedbackPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 20


class TeacherListCreateTestFeedbackAPIView(generics.ListCreateAPIView):
    pagination_class = FeedbackPagination
    permission_classes = [IsTeacher]
    
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = TestFeedbackFilterSet
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]  # Default ordering

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TeacherTestFeedbackCreateSerializer
        return TestFeedbackListSerializer

    def get_queryset(self):
        # For list views, we enforce providing test_id
        if self.request.method != "GET":
            return TestFeedback.objects.all()
            
        test_id = self.request.query_params.get("test_id")
        if not test_id:
            raise ValidationError({"test_id": "This query parameter is required."})
            
        queryset = TestFeedback.objects.select_related("teacher__user").filter(test_id=test_id)
        
        # Sort AI feedback first, then by created_at descending
        queryset = queryset.annotate(
            is_ai_sort_tier=Case(
                When(created_by="A", then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by("is_ai_sort_tier", "-created_at")
        
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if user.role != "T":
            raise PermissionDenied("Only teachers can submit feedback via this endpoint.")
            
        try:
            teacher = Teacher.objects.get(user=user)
        except Teacher.DoesNotExist:
            raise PermissionDenied("Teacher profile not found for this user.")
            
        serializer.save(teacher=teacher, created_by="T")

    @extend_schema(
        summary="Create teacher feedback for a test",
        description=dedent("""\
            Allows an authenticated and verified Teacher to post feedback for a specific test.
            
            ### How to Test (Auth Required)
            1. Go to `POST /api/accounts/login`
            2. Login with a Verified Teacher account: 
               - Username: `teacher10` (or 11, 12)
               - Password: `123`
            3. Copy the `access` token.
            4. Click 'Authorize' at the top of Swagger and paste the token.

            ### Test Cases
            **1. Successful Feedback Creation**
            * **Method:** `POST`
            * **URL:** `/api/feedback/test-feedbacks`
            * **Body:** `{"test_id": 1, "comment": "Good job, but re-evaluate question 4."}`
            * **Result:** `201 Created`

            **2. Test Not Found**
            * **Method:** `POST`
            * **URL:** `/api/feedback/test-feedbacks`
            * **Body:** `{"test_id": 999, "comment": "Ghost test feedback"}`
            * **Result:** `400 Bad Request` with `{"test_id": ["Valid test not found."]}`

            **3. Forbidden Access (Student or Unverified Teacher)**
            * **Result:** `403 Forbidden` (`{"detail": "Only teachers can access this resource."}`)
        """),
        tags=["test-feedback"],
        examples=[
            OpenApiExample(
                "Successful Feedback",
                request_only=True,
                value={
                    "test_id": 1,
                    "comment": "The reading passage is a bit too challenging for B1 level. Please review question 4 again."
                }
            )
        ],
        responses={
            201: OpenApiResponse(description="Feedback posted successfully"),
            400: OpenApiResponse(description="Bad request, validation error"),
            403: OpenApiResponse(description="Permission denied, user is not a teacher or not verified"),
            404: OpenApiResponse(description="Test not found"),
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    @extend_schema(
        summary="List feedback for a specific test",
        tags=["test-feedback"],
        description=dedent("""\
            Retrieves a paginated list of feedback comments for a given `test_id`.
            
            ### 🔑 How to Test (Auth Required)
            1. Login (`POST /api/accounts/login`) with `teacher10@example.com` / `password123`.
            2. Use the `access` token for Authorization.
            
            **Sorting Rules:**
            - AI feedback (`created_by="A"`) is always pinned to the top.
            - Teacher feedback (`created_by="T"`) appears below AI feedback, sorted from newest to oldest.

            ### Test Cases
            **1. Successful Listing (Default)**
            * **URL:** `/api/feedback/test-feedbacks?test_id=1`
            * **Result:** `200 OK` (AI feedback is strictly the first item, followed by page 1 of Teacher feedback).

            **2. Filter by Teacher Feedback Only**
            * **URL:** `/api/feedback/test-feedbacks?test_id=1&created_by=T`
            * **Result:** `200 OK` (Only shows feedback added by human teachers).

            **3. Sort Teacher Feedback**
            * **URL:** `/api/feedback/test-feedbacks?test_id=1&ordering=-created_at`
            * **Result:** `200 OK` (Newest feedback first; default ordering is `-created_at`).

            **4. Missing Required Parameter**
            * **URL:** `/api/feedback/test-feedbacks`
            * **Result:** `400 Bad Request` (`{"test_id": "This query parameter is required."}`)
        """),
        parameters=[
            OpenApiParameter(
                name="test_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="ID of the test to retrieve feedback for",
                required=True,
            ),
            OpenApiParameter(
                name="created_by",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter feedback by author type",
                required=False,
                enum=["A", "T"],
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Sort by created_at; use -created_at for newest first",
                required=False,
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Page number",
                required=False,
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of items per page",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Successfully retrieved test feedback"),
            400: OpenApiResponse(description="Bad Request: Missing test_id parameter"),
            401: OpenApiResponse(description="Unauthorized"),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class TeacherRetrieveUpdateDestroyTestFeedbackAPIView(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [CustomTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsTeacher]
    serializer_class = TeacherTestFeedbackUpdateSerializer
    lookup_field = "id"
    lookup_url_kwarg = "feedback_id"

    def get_queryset(self):
        return TestFeedback.objects.select_related("teacher__user").all()

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method in ["PATCH", "PUT", "DELETE"]:
            if not hasattr(request.user, "teacher") or obj.teacher != request.user.teacher:
                raise PermissionDenied("You can only edit or delete your own feedback.")

    @extend_schema(
        summary="Retrieve a specific feedback",
        description="Retrieves the details of a single feedback comment.",
        tags=["test-feedback"],
        responses={
            200: OpenApiResponse(description="Successfully retrieved feedback"),
            404: OpenApiResponse(description="Feedback not found"),
        }
    )
    def get(self, request, *args, **kwargs):
        self.serializer_class = TestFeedbackListSerializer
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update feedback (Not Allowed)",
        description="PUT method is not supported. Please use PATCH instead.",
        tags=["test-feedback"],
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
        summary="Partially update a feedback",
        description=dedent("""\
            Allows a teacher to update a feedback comment they previously created.
            
            ### How to Test (Auth Required)
            1. Login (`POST /api/accounts/login`) with `teacher10` (password: `123`).
            2. Use the `access` token for Authorization.
            3. According to seed data, `teacher10` authored Feedback ID `2` (for Test 1). 
            4. Make a `PATCH` request to `/api/feedback/test-feedbacks/2` with the updated `comment`.

            ### Test Cases
            **1. Successful Update**
            * **Method:** `PATCH`
            * **URL:** `/api/feedback/test-feedbacks/2`
            * **Body:** `{"comment": "I changed my mind, actually the questions are fine."}`
            * **Result:** `200 OK`

            **2. Forbidden Access (Not the creator)**
            * **Auth:** Bearer Token (using `teacher11` / `123`)
            * **URL:** `/api/feedback/test-feedbacks/2`
            * **Result:** `403 Forbidden` (`{"detail": "You can only edit or delete your own feedback."}`)
        """),
        tags=["test-feedback"],
        responses={
            200: OpenApiResponse(description="Successfully updated the feedback"),
            400: OpenApiResponse(description="Bad request"),
            403: OpenApiResponse(description="Forbidden (Not the owner)"),
            404: OpenApiResponse(description="Feedback not found"),
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a feedback",
        description=dedent("""\
            Allows a teacher to delete a feedback comment they previously created.
            
            ### How to Test (Auth Required)
            1. Login (`POST /api/accounts/login`) with `teacher10` (password: `123`).
            2. Use the `access` token for Authorization.
            3. Make a `DELETE` request to `/api/feedback/test-feedbacks/2`

            ### Test Cases
            **1. Successful Deletion**
            * **Method:** `DELETE`
            * **URL:** `/api/feedback/test-feedbacks/2`
            * **Result:** `204 No Content`

            **2. Forbidden Access (Not the creator)**
            * **Method:** `DELETE`
            * **Auth:** Bearer Token (using `teacher11` / `123`)
            * **URL:** `/api/feedback/test-feedbacks/2`
            * **Result:** `403 Forbidden` (`{"detail": "You can only edit or delete your own feedback."}`)
        """),
        tags=["test-feedback"],
        responses={
            204: OpenApiResponse(description="Successfully deleted the feedback"),
            403: OpenApiResponse(description="Forbidden (Not the owner)"),
            404: OpenApiResponse(description="Feedback not found"),
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)