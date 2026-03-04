import base64
import json
import re

import requests
from django.db import transaction

from accounts.models import Student
from vertexai.generative_models import Part


IMG_TAG_PATTERN = re.compile(r"<img\b[^>]*>", flags=re.IGNORECASE)
DATA_SRC_PATTERN = re.compile(
    r"src\s*=\s*([\"'])data:(image/[^;]+);base64,([^\"']+)\1",
    flags=re.IGNORECASE | re.DOTALL,
)
WIDTH_PATTERN = re.compile(r"\bwidth\s*=\s*[\"']?(\d+)[\"']?", flags=re.IGNORECASE)
HEIGHT_PATTERN = re.compile(r"\bheight\s*=\s*[\"']?(\d+)[\"']?", flags=re.IGNORECASE)

def _build_image_item(
    original_tag: str,
    image_id: str,
    marker: str,
    mime_type: str,
    b64_payload: str,
    position_index: int,
):
    width_match = WIDTH_PATTERN.search(original_tag)
    height_match = HEIGHT_PATTERN.search(original_tag)

    return {
        "id": image_id,
        "marker": marker,
        "mime_type": mime_type,
        "width": int(width_match.group(1)) if width_match else None,
        "height": int(height_match.group(1)) if height_match else None,
        "bytes_base64": b64_payload,
        "position_index": position_index,
    }

def _replace_img_tag(original_tag: str, image_index: int):
    """
    Process a single <img> tag.

    Returns:
    - replaced_tag: transformed tag (or original if not base64/invalid)
    - image_item: extracted image metadata (or None)
    """
    src_match = DATA_SRC_PATTERN.search(original_tag)
    if not src_match:
        return original_tag, None

    mime_type = src_match.group(2).strip().lower()
    b64_payload = re.sub(r"\s+", "", src_match.group(3))

    try:
        base64.b64decode(b64_payload, validate=True)
    except Exception:
        return original_tag, None

    image_id = f"IMG_{image_index}"
    marker = f"[[{image_id}]]"

    replaced_tag = DATA_SRC_PATTERN.sub(
        lambda m: f'src={m.group(1)}{marker}{m.group(1)}', original_tag, count=1
    )

    if "data-ai-image-id=" not in replaced_tag:
        replaced_tag = replaced_tag.replace("<img", f'<img data-ai-image-id="{image_id}"', 1)

    image_item = _build_image_item(
        original_tag=original_tag,
        image_id=image_id,
        marker=marker,
        mime_type=mime_type,
        b64_payload=b64_payload,
        position_index=image_index,
    )

    return replaced_tag, image_item

def process_prompt_html_images(raw_html: str):
    """
    Keep HTML content as-is, only replace base64 image src with markers and
    extract image payloads for later multimodal AI request.
    """
    html_content = raw_html or ""
    image_items = []
    image_counter = 0

    def _replace_match(match):
        nonlocal image_counter
        original_tag = match.group(0)
        candidate_tag, image_item = _replace_img_tag(original_tag, image_counter + 1)

        if image_item:
            image_counter += 1
            image_items.append(image_item)

        return candidate_tag

    processed_html = IMG_TAG_PATTERN.sub(_replace_match, html_content)
    return processed_html, image_items

def format_writing_criteria_text(criteria_rows):
    """
    Build a human-readable writing criteria text block from template rows.
    """
    if not criteria_rows:
        return "No criteria template is available for this level."

    lines = []
    for row in criteria_rows:
        lines.append(
            "\n".join(
                [
                    f"Band {row['band']} ({row['level']}):",
                    f"- Content: {row['content'] or ''}",
                    f"- Communicative Achievement: {row['communicative_achievement'] or ''}",
                    f"- Organisation: {row['organisation'] or ''}",
                    f"- Language: {row['language'] or ''}",
                ]
            )
        )

    return "\n\n".join(lines)

def build_ai_prompt_text(
    productive_test_format,
    test_level,
    processed_html_str,
    writing_criteria_text,
    student_answer_text,
):
    """
    Construct the main prompt text for the Gemini model.
    """
    return (
        "You are an English writing examiner.\n\n"
        f"I have a {productive_test_format} writing test at CEFR level {test_level}.\n\n"
        "The test prompt is originally stored as HTML. Images in the HTML were stored as base64, "
        "then extracted and sent to you separately as ordered images. In the HTML text, image positions "
        "are marked with placeholders like [[IMG_1]], [[IMG_2]], etc. Please read the HTML text and "
        "the corresponding images together (if images are provided).\n\n"
        "Prompt HTML:\n"
        f"{processed_html_str}\n\n"
        "Scoring criteria:\n"
        f"{writing_criteria_text}\n\n"
        "Student response:\n"
        f"{student_answer_text}\n\n"
        "Instructions:\n"
        "1. Evaluate the student response against each scoring criterion (Content, Communicative Achievement, "
        "Organisation, Language).\n"
        "2. Do NOT write free text paragraphs. Instead, produce a structured JSON object with EXACTLY the following shape:\n\n"
        "{\n"
        '  "content": {\n'
        '    "band": <integer from the given scale>,\n'
        '    "strengths": "<short paragraph describing the main strengths for Content>",\n'
        '    "improvements": "<short paragraph describing only necessary improvements for Content, or \'None\' if there is nothing important to fix>"\n'
        "  },\n"
        '  "communicative_achievement": {\n'
        '    "band": <integer>,\n'
        '    "strengths": "<short paragraph describing the main strengths for Communicative Achievement>",\n'
        '    "improvements": "<short paragraph describing only necessary improvements for Communicative Achievement, or \'None\' if there is nothing important to fix>"\n'
        "  },\n"
        '  "organisation": {\n'
        '    "band": <integer>,\n'
        '    "strengths": "<short paragraph describing the main strengths for Organisation>",\n'
        '    "improvements": "<short paragraph describing only necessary improvements for Organisation, or \'None\' if there is nothing important to fix>"\n'
        "  },\n"
        '  "language": {\n'
        '    "band": <integer>,\n'
        '    "strengths": "<short paragraph describing the main strengths for Language>",\n'
        '    "improvements": "<short paragraph describing only necessary improvements for Language, or \'None\' if there is nothing important to fix>"\n'
        "  },\n"
        '  "overall": {\n'
        '    "summary": "<3–5 sentences summarising the overall performance at CEFR level '
        f'{test_level}>",\n'
        '    "next_actions": "<2–4 concrete suggestions for what the student should do next to improve>"\n'
        "  }\n"
        "}\n\n"
        "3. The value of each field must be plain text only (no nested JSON, no markdown syntax).\n"
        "4. CRITICAL: Return ONLY the raw JSON object. Do NOT wrap it in markdown code fences (```json ... ```). "
        "Do NOT add any prefix text like 'json' or 'Here is the JSON:'. Do NOT add any suffix text or explanations. "
        "Start your response directly with '{' and end with '}'.\n"
        "5. Do not explain the JSON, do not add any extra text before or after it. Return ONLY the JSON object.\n"
        "6. Do not end any sentence halfway; always complete your thoughts.\n"
        "7. Do not invent missing prompt details; rely only on the provided HTML and images.\n"
    )

def load_prompt_html(prompt_source):
    """
    Load prompt HTML either from a URL or raw HTML string.
    """
    prompt_source = (prompt_source or "").strip()
    if not prompt_source:
        return "", False

    if prompt_source.startswith("http://") or prompt_source.startswith("https://"):
        try:
            response = requests.get(prompt_source, timeout=15)
            if response.status_code == 200:
                return response.text, True
        except requests.RequestException:
            return prompt_source, False

    return prompt_source, False

def build_vertex_parts(ai_prompt_text, prompt_images):
    """
    Build multimodal parts (text + images) for Vertex AI Gemini.
    """
    parts = [ai_prompt_text]
    for image in prompt_images:
        try:
            image_bytes = base64.b64decode(image["bytes_base64"], validate=True)
            parts.append(Part.from_data(data=image_bytes, mime_type=image["mime_type"]))
        except Exception:
            # Ignore invalid image payloads silently to avoid breaking the whole request.
            continue
    return parts


def build_speaking_vertex_parts(ai_prompt_text: str, audio_gcs_uri: str, mime_type: str):
    """
    Build multimodal parts (text + audio) for Vertex AI Gemini speaking evaluation.

    The audio is provided as a GCS URI (gs://...) which Gemini can fetch directly.
    """
    parts = [ai_prompt_text]
    if audio_gcs_uri:
        try:
            parts.append(
                Part.from_uri(
                    uri=audio_gcs_uri,
                    mime_type=mime_type,
                )
            )
        except Exception:
            # If audio part construction fails, we still send text-only prompt
            # so that the request does not break completely.
            pass
    return parts

def extract_model_text(response):
    """
    Extract the first non-empty text from a Gemini model response.
    """
    text = getattr(response, "text", None)
    if text:
        return text.strip()

    candidates = getattr(response, "candidates", []) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            candidate_text = getattr(part, "text", None)
            if candidate_text:
                return candidate_text.strip()
    return ""

def parse_feedback_json(feedback_text):
    """
    Best-effort parsing of model output into JSON.

    Handles common patterns like:
    - leading 'json' line
    - ```json ... ``` code fences
    - JSON string that itself contains JSON.
    """
    if not feedback_text:
        return None

    text = feedback_text.strip()

    # Strip markdown code fences if present.
    if text.startswith("```"):
        # Remove opening ```
        text = text[3:].lstrip()
        # Optional language tag like "json"
        if text.lower().startswith("json"):
            text = text[4:].lstrip(" \n:")
        # Remove trailing ``` if exists
        end_idx = text.rfind("```")
        if end_idx != -1:
            text = text[:end_idx]
    else:
        # If the first line is just "json", drop it.
        lines = text.splitlines()
        if lines and lines[0].strip().lower() == "json":
            text = "\n".join(lines[1:]).strip()

    # First attempt: direct JSON
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    # If the model returned a JSON string that itself contains JSON, try one more level.
    if isinstance(parsed, str):
        inner = parsed.strip()
        if inner.startswith("{") and inner.endswith("}"):
            try:
                return json.loads(inner)
            except json.JSONDecodeError:
                # Fall back to the string itself
                return parsed

    return parsed

def deduct_ai_turn(student_id):
    """
    Atomically deduct one AI turn from a student's weekly or bonus quota.
    """
    with transaction.atomic():
        student = Student.objects.select_for_update().get(pk=student_id)
        if student.weekly_ai_turn > 0:
            student.weekly_ai_turn -= 1
            turn_source = "weekly_ai_turn"
        elif student.bonus_ai_turn > 0:
            student.bonus_ai_turn -= 1
            turn_source = "bonus_ai_turn"
        else:
            return None, None

        student.save(update_fields=["weekly_ai_turn", "bonus_ai_turn"])
        return student, turn_source
