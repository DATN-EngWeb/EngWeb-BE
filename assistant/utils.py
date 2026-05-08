import json
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from google import genai
from google.genai import types

from .models import AssistantConversation, AssistantQuota
from .prompts import SYSTEM_PROMPTS, USER_PROMPTS


MODE_PREFIX_MAP = {
    AssistantConversation.MODE_TRANSLATE: "Translate",
    AssistantConversation.MODE_GRAMMAR: "Grammar",
    AssistantConversation.MODE_VOCABULARY: "Vocabulary",
    AssistantConversation.MODE_BRAINSTORM: "Brainstorm",
    AssistantConversation.MODE_GENERAL: "Chat",
}


def normalize_mode(mode):
    value = (mode or "").strip().lower()
    allowed = {item[0] for item in AssistantConversation.MODE_CHOICES}
    if value in allowed:
        return value
    return AssistantConversation.MODE_GENERAL


def generate_conversation_title(mode, first_message, source_text=None):
    seed = (source_text or first_message or "").strip()
    seed = " ".join(seed.split())
    if not seed:
        return "New Chat", True

    seed = seed[:50].rstrip()
    prefix = MODE_PREFIX_MAP.get(normalize_mode(mode), "Chat")
    return f"{prefix}: {seed}", True


def _quota_defaults_for_user(user):
    default_limit = getattr(settings, "ASSISTANT_QUOTA_DEFAULT_LIMIT", 50)
    default_period = getattr(settings, "ASSISTANT_QUOTA_DEFAULT_PERIOD_SECONDS", 12 * 60 * 60)

    return max(int(default_limit), 1), max(int(default_period), 60)


def _localize_reset_at(reset_at):
    if reset_at is None:
        return None
    return timezone.localtime(reset_at)


@transaction.atomic
def get_or_create_quota(user):
    quota = AssistantQuota.objects.select_for_update().filter(user=user).first()
    if quota:
        return quota

    limit, period_seconds = _quota_defaults_for_user(user)
    quota = AssistantQuota.objects.create(
        user=user,
        limit=limit,
        used=0,
        period_seconds=period_seconds,
        period_start=timezone.now(),
    )
    return quota


@transaction.atomic
def check_and_consume_quota(user, amount=1, reserve=True):
    quota = get_or_create_quota(user)
    now = timezone.now()

    reset_at = quota.period_start + timedelta(seconds=quota.period_seconds)
    if now >= reset_at:
        quota.used = 0
        quota.period_start = now
        reset_at = quota.period_start + timedelta(seconds=quota.period_seconds)

    if quota.used + amount > quota.limit:
        quota.save(update_fields=["used", "period_start", "updated_at"])
        return False, {
            "remaining": 0,
            "limit": quota.limit,
            "reset_at": _localize_reset_at(reset_at),
        }

    if reserve:
        quota.used += amount
        quota.save(update_fields=["used", "period_start", "updated_at"])

    remaining = max(quota.limit - quota.used, 0)
    return True, {
        "remaining": remaining,
        "limit": quota.limit,
        "reset_at": _localize_reset_at(reset_at),
    }


@transaction.atomic
def release_quota(user, amount=1):
    quota = AssistantQuota.objects.select_for_update().filter(user=user).first()
    if not quota:
        return
    quota.used = max(quota.used - amount, 0)
    quota.save(update_fields=["used", "updated_at"])


def get_quota_status(user):
    quota = get_or_create_quota(user)
    now = timezone.now()
    reset_at = quota.period_start + timedelta(seconds=quota.period_seconds)

    if now >= reset_at:
        quota.used = 0
        quota.period_start = now
        quota.save(update_fields=["used", "period_start", "updated_at"])
        reset_at = quota.period_start + timedelta(seconds=quota.period_seconds)

    return {
        "remaining": max(quota.limit - quota.used, 0),
        "limit": quota.limit,
        "reset_at": _localize_reset_at(reset_at),
    }


def _build_system_prompt(mode):
    mode = normalize_mode(mode)
    return SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS[AssistantConversation.MODE_GENERAL])


def _format_history_messages(history_messages):
    if not history_messages:
        return ""

    lines = ["Recent conversation history:"]
    for item in history_messages:
        role = (item.get("role") or "unknown").lower()
        content = " ".join((item.get("content") or "").split())
        if not content:
            continue

        if role == "assistant":
            role_label = "assistant"
        elif role == "user":
            role_label = "user"
        else:
            role_label = role

        # Keep each history item compact to avoid prompt bloat.
        lines.append(f"- {role_label}: {content[:300]}")

    if len(lines) == 1:
        return ""

    return "\n".join(lines)


def _build_user_prompt(mode, message, context, history_messages=None):
    mode = normalize_mode(mode)
    context = context or {}

    level = (context.get("level") or "").strip()
    source_text = (context.get("source_text") or "").strip()

    common_prefix = []
    if level:
        common_prefix.append(f"Learner level: {level}")
    if source_text:
        common_prefix.append(f"Source text: {source_text}")

    history_text = _format_history_messages(history_messages)
    if history_text:
        common_prefix.append(history_text)

    prefix_text = "\n".join(common_prefix)
    if prefix_text:
        prefix_text += "\n\n"


    target_lang = context.get("target_language") or context.get("language")
    target_lang = str(target_lang).strip() if target_lang else "the same language as the user's message"

    lang_instruction = (
        f"Output language: {target_lang}. "
        "All explanatory fields (for example: notes, explanation, examples, useful_vocabulary, linking_words, english_tip) "
        "must be written in the same language the user is using to communicate. "
    )

    prompt_template = USER_PROMPTS.get(mode, USER_PROMPTS[AssistantConversation.MODE_GENERAL])
    return f"{prefix_text}{lang_instruction}\n\n{prompt_template.format(message=message)}"


def _temperature_for_mode(mode):
    mode = normalize_mode(mode)
    if mode in {
        AssistantConversation.MODE_TRANSLATE,
        AssistantConversation.MODE_GRAMMAR,
        AssistantConversation.MODE_VOCABULARY,
    }:
        return 0.2
    if mode == AssistantConversation.MODE_BRAINSTORM:
        return 0.7
    return 0.5


def call_assistant_model(mode, message, context=None, history_messages=None):
    system_prompt = _build_system_prompt(mode)
    user_prompt = _build_user_prompt(mode, message, context, history_messages=history_messages)

    prompt = f"{system_prompt}\n\n{user_prompt}"

    client = genai.Client(
        vertexai=True,
        project=settings.VERTEX_AI_PROJECT_ID,
        location=settings.VERTEX_AI_LOCATION,
    )

    response = client.models.generate_content(
        model=settings.VERTEX_AI_MODEL,
        contents=[types.Part.from_text(text=prompt)],
        config=types.GenerateContentConfig(
            temperature=_temperature_for_mode(mode),
        ),
    )

    text = extract_model_text(response)
    parsed = parse_json_maybe(text)

    usage = getattr(response, "usage_metadata", None)
    usage_data = {
        "prompt_token_count": getattr(usage, "prompt_token_count", None),
        "completion_token_count": getattr(usage, "candidates_token_count", None),
        "total_token_count": getattr(usage, "total_token_count", None),
    }

    return text, parsed, usage_data


def extract_model_text(response):
    text = getattr(response, "text", None)
    if text:
        return text.strip()

    candidates = getattr(response, "candidates", []) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            part_text = getattr(part, "text", None)
            if part_text:
                return part_text.strip()
    return ""


def parse_json_maybe(raw_text):
    if not raw_text:
        return None

    text = raw_text.strip()

    if text.startswith("```"):
        text = text[3:].lstrip()
        if text.lower().startswith("json"):
            text = text[4:].lstrip(" \n:")
        end_idx = text.rfind("```")
        if end_idx != -1:
            text = text[:end_idx]

    lines = text.splitlines()
    if lines and lines[0].strip().lower() == "json":
        text = "\n".join(lines[1:]).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, str):
        inner = parsed.strip()
        if inner.startswith("{") and inner.endswith("}"):
            try:
                return json.loads(inner)
            except json.JSONDecodeError:
                return parsed

    return parsed
