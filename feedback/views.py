from accounts.authentication import CustomTokenAuthentication
from accounts.models import Student
from test_histories.models import ProductiveTestHistory
from tests.models import SpeakingCriteriaTemplate, WritingCriteriaTemplate
from .utils import (
    build_ai_prompt_text,
    build_vertex_parts,
    build_speaking_vertex_parts,
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
            vertexai.init(
                project=settings.VERTEX_AI_PROJECT_ID,
                location=settings.VERTEX_AI_LOCATION,
            )
            model = GenerativeModel(settings.VERTEX_AI_MODEL)
            parts = build_speaking_vertex_parts(
                ai_prompt_text=ai_prompt_text,
                audio_gcs_uri=audio_gcs_uri,
                mime_type=audio_mime,
            )
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
