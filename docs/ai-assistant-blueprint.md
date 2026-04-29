# AI Assistant Blueprint (refined)

## Tóm tắt

Tài liệu này mô tả thiết kế cho một "AI assistant" tích hợp với hạ tầng Django + Vertex AI hiện có trong repo. Hệ thống có các mode học tiếng Anh (`translate`, `grammar`, `vocabulary`, `brainstorm`) và một mode `general` để chat đa lĩnh vực khi người dùng không chọn mode.

Tài liệu đã được tinh chỉnh để làm rõ API contract, cơ chế quota (time-window) riêng cho assistant, hành vi quota atomicity, xử lý lỗi, bảo mật, giám sát và lộ trình rollout.

---

## 1. Cấu trúc dữ liệu (MVP)

Ghi chú: giữ schema đơn giản và mở rộng được.

### 1.1 `assistant_conversation`

- `id`
- `user` (FK → `accounts.User`)
- `title` (short, backend-generated if omitted)
- `is_title_auto` (bool, default=true)
- `mode` (enum: `translate`, `grammar`, `vocabulary`, `brainstorm`, `general`)
- `target_skill` (`R`, `W`, `S`, `L`, `GENERAL`)
- `level` (CEFR or internal id)
- `system_prompt_version` (string)
- `last_message_at`, `is_archived`, `created_at`, `updated_at`

Index: `user, last_message_at`.

### 1.2 `assistant_message`

- `id`
- `conversation` (FK → `assistant_conversation`)
- `role` (`system`, `user`, `assistant`, `tool`)
- `content` (text)
- `token_usage_prompt`, `token_usage_completion`, `token_usage_total` (nullable ints)
- `status` (`pending`, `completed`, `failed`)
- `created_at`

Notes: store raw assistant text in `content`.

### 1.3 (Optional) `assistant_feedback_context`

Server-side personalization snapshot: `user`, `summary`, `weak_points` (JSON), `recommended_topics` (JSON), `recent_errors` (JSON), `updated_at`.

Keep optional for MVP; context can be passed with each request instead.

---

## 2. API contract (tightened)

Create app `assistant`. All endpoints require authentication (use existing `CustomTokenAuthentication`).

Design goals:

- Predictable schemas
- Clear status codes: 200 (OK), 201 (Created), 429 (Quota), 502 (AI service), 403 (Forbidden), 400 (Bad request)
- Small, validated JSON payloads

### 2.1 POST /api/assistant/conversations

Create a new conversation.

Request:

```json
{
  "mode": "grammar",
  "target_skill": "GENERAL",
  "level": "B1"
}
```

`mode` là optional. Nếu FE không gửi, backend default `mode = "general"`.

`title` là optional. Nếu FE không gửi, backend tự sinh từ `source_text` hoặc `first_message`.

Response: 201 Created with conversation object.

Response example:

```json
{
  "id": 12,
  "title": "Grammar: used to vs be used to",
  "is_title_auto": true,
  "mode": "grammar",
  "target_skill": "GENERAL",
  "level": "B1"
}
```

### 2.2 GET /api/assistant/conversations

List conversations for the authenticated user (support pagination).

### 2.3 GET /api/assistant/conversations/{id}

Return conversation metadata + recent messages (support `?limit=` and `?before=`).

### 2.4 POST /api/assistant/conversations/{id}/messages

User sends a message; server returns assistant reply.

Request (MVP):

```json
{
  "message": "Explain the difference between 'used to' and 'be used to'.",
  "context": {
    "skill": "GRAMMAR",
    "level": "B1",
    "source_text": "I used to live in Hanoi."
  }
}
```

Nếu request không chứa mode thì backend dùng mode của conversation; nếu conversation chưa có mode thì fallback `general`.

Server steps (recommended):

1. Authenticate and verify conversation ownership.
2. Start DB transaction.
3. Reserve quota via `check_and_consume_quota(user, amount=1, reserve=True)` (see section 11).
4. Persist user message as `assistant_message` (role=user, status=pending).
5. Build prompt and call Vertex AI.
6. On success: parse response, persist assistant message (status=completed), record token usage, commit transaction.
7. On failure: rollback reservation (or decrement used), mark message failed, return 502/appropriate error.

Success response (200):

```json
{
  "message_id": 101,
  "assistant_message_id": 102,
  "answer": "...",
  "mode": "grammar",
  "usage": {
    "prompt_token_count": 812,
    "completion_token_count": 241,
    "total_token_count": 1053
  },
  "quota": { "remaining": 12, "limit": 50, "reset_at": "2026-05-08T12:00:00Z" }
}
```

Quota-denied (429):

```json
{
  "detail": "Assistant quota exceeded.",
  "quota": { "remaining": 0, "limit": 50, "reset_at": "2026-05-01T12:00:00Z" }
}
```

AI error (502):

```json
{ "detail": "AI service error", "error": "Timeout/ServiceUnavailable" }
```

### 2.5 DELETE /api/assistant/conversations/{id}

Soft-delete or archive conversation.

### 2.6 PATCH /api/assistant/conversations/{id}

Rename conversation title (manual override by user).

Request:

```json
{ "title": "Grammar - used to exercises" }
```

Response: updated conversation with `is_title_auto=false`.

### 2.7 GET /api/assistant/quota

Return `{ remaining, limit, reset_at }` for current user.

### 2.8 Title generation rules (backend)

Để FE không phải "biết trước title", backend dùng rule cố định:

1. Ưu tiên `context.source_text` nếu có, nếu không lấy từ `message` đầu tiên.
2. Chuẩn hoá text: trim, bỏ xuống dòng, rút gọn khoảng trắng.
3. Cắt độ dài 40-60 ký tự (ví dụ 50) để hiển thị sidebar.
4. Thêm prefix theo mode:
   - `translate` -> `Translate: ...`
   - `grammar` -> `Grammar: ...`
   - `vocabulary` -> `Vocabulary: ...`
   - `brainstorm` -> `Brainstorm: ...`

- `general` -> `Chat: ...`

5. Nếu text rỗng hoặc quá ngắn -> fallback: `New Chat`.

Pseudo-code:

```python
def generate_conversation_title(mode, first_message, source_text=None):
  seed = (source_text or first_message or "").strip()
  seed = " ".join(seed.split())
  if not seed:
    return "New Chat", True

  seed = seed[:50].rstrip()
  prefix_map = {
    "translate": "Translate",
    "grammar": "Grammar",
    "vocabulary": "Vocabulary",
    "brainstorm": "Brainstorm",
    "general": "Chat",
  }
  prefix = prefix_map.get(mode, "Chat")
  return f"{prefix}: {seed}", True
```

---

## 3. Model choice & parameters

Use Vertex AI Gemini as configured in `english_app/settings.py`.

Guidelines:

- Use low temperature for deterministic tasks (translation, grammar, vocabulary), medium for general Q&A, and higher for brainstorming.
- Request strict JSON output when UI depends on structure; validate before accepting.
- Log model name and token usage for billing and debugging.

Suggested temperature ranges:

- `translation`, `grammar`, `vocabulary`: 0.1–0.3
- `brainstorm`: 0.6–0.8
- `general`: 0.4–0.6

Resilience:

- Retry with exponential backoff for transient Vertex errors (cap retries), and return 502 if persistent.
- Provide human-readable fallback when JSON parse fails.

---

## 4. Prompt templates and output schemas

### 4.1 System prompt chung

```text
You are an English learning assistant.

Your scope is limited to:
- translation
- grammar explanation
- vocabulary explanation
- brainstorming writing ideas
- general question answering

Rules:
- Stay within English-learning tasks only.
- Keep explanations clear, concise, and suitable for the learner level.
- For `general` mode, you may answer broader topics with concise, safe responses.
- For non-`general` modes, keep responses inside English-learning tasks.
- Prefer structured output for easier UI rendering.
```

### 4.2 Translation mode

```text
Mode: translation

Input text:
{user_text}

Requirements:
1. Translate naturally into Vietnamese.
2. If sentence is complex, provide a literal translation too.
3. Highlight difficult words/idioms and subtle meaning differences.
```

Suggested output JSON:

```json
{
  "translation": "...",
  "literal_translation": "...",
  "notes": ["...", "..."]
}
```

### 4.3 Grammar mode

```text
Mode: grammar

Input sentence:
{user_text}

Requirements:
1. Identify the grammar point.
2. Explain the rule in simple language.
3. Explain why this sentence uses that form.
4. Provide 2-3 additional examples.
5. Mention common mistakes.
```

Suggested output JSON:

```json
{
  "grammar_point": "...",
  "explanation": "...",
  "examples": ["...", "..."],
  "common_mistakes": ["...", "..."]
}
```

### 4.4 Vocabulary mode

```text
Mode: vocabulary

Input word or phrase:
{user_text}

Requirements:
1. Explain meaning in context.
2. Add pronunciation tip if useful.
3. Provide collocations and synonyms/antonyms when relevant.
4. Provide examples appropriate for user level.
```

Suggested output JSON:

```json
{
  "meaning": "...",
  "pronunciation_tip": "...",
  "collocations": ["...", "..."],
  "synonyms": ["..."],
  "antonyms": ["..."],
  "examples": ["...", "..."]
}
```

### 4.5 Brainstorm mode

```text
Mode: brainstorm

Topic:
{user_text}

Requirements:
1. Generate 5-8 relevant ideas.
2. Group ideas by subtopic.
3. Suggest a simple outline.
4. Provide useful vocabulary/linking words.
5. Give sample thesis statement or topic sentences.
```

Suggested output JSON:

```json
{
  "ideas": ["...", "..."],
  "outline": ["Introduction", "Body 1", "Body 2", "Conclusion"],
  "useful_vocabulary": ["...", "..."],
  "linking_words": ["Firstly", "Moreover", "In conclusion"],
  "sample_thesis": "...",
  "topic_sentences": ["...", "..."]
}
```

### 4.6 General mode

```text
Mode: general

User question:
{user_text}

Requirements:
1. Answer concisely and accurately.
2. Use simple structure: short answer + key points.
3. If the user asks to learn English from the topic, include an optional "English learning tip".
4. Do not produce unsafe or policy-violating content.
```

Suggested output JSON:

```json
{
  "answer": "...",
  "key_points": ["...", "..."],
  "english_tip": "..."
}
```

Always validate assistant JSON against expected schema; log parse failures.

---

## 5. Backend flow & atomicity

Flow summary:

1. Authenticate user.
2. Fetch conversation, user profile, last messages.
3. Check and reserve quota.
4. Persist user message (status=pending).
5. Build prompt and call model.
6. On success: persist assistant message (status=completed), record token usage, commit.
7. On failure: rollback reservation, mark message failed, return 502.

Atomicity recommendation:

- Use DB transactions and `select_for_update()` when reserving quota to avoid race conditions.
- Prefer reservation-then-commit policy (rollback on transient failures) to avoid charging users for failed calls.

Logging & metrics:

- Persist token usage per message. Export metrics: requests/sec, errors, parse failures, quota denials, token consumption.

---

## 6. Reuse existing code

Repo already contains AI helpers in `feedback/views.py` and `feedback/utils.py` — extract Vertex call and parsing to `assistant/utils.py` or `utils/ai_client.py`.

Core utilities to provide:

- `build_assistant_prompt(mode, user_level, context, history)`
- `generate_with_vertex_ai(parts, temperature)`
- `parse_assistant_response(text, schema)`
- `summarize_conversation(history)`

Add unit tests for parsing and prompt building.

---

## 7. Frontend suggestions

- Display conversations list, chat pane, input + mode selector.
- Show remaining quota and reset countdown.
- For `brainstorm`, render ideas and outline in separate blocks for quick copy/reuse.
- Add quick actions: `Explain simpler`, `More examples`, `Check my sentence`, `Make it more natural`, `Give me a quiz`.

Use standard request/response UI.

---

## 8. Scope, security & policy

- `general` mode allows broader domain Q&A.
- `translate`, `grammar`, `vocabulary`, `brainstorm` remain focused on English-learning tasks.
- Enforce content policy: disallow hateful, sexual, illegal content.
- Validate input sizes and sanitize dangerous content.

Permissions:

- Use existing authentication; ensure rate-limits and quota checks are applied server-side.

---

## 9. MVP checklist

1. Implement assistant models and messages.
2. Implement `AssistantQuota` and `check_and_consume_quota` with reservation semantics.
3. Implement `POST /api/assistant/conversations/{id}/messages` view integrating quota and AI call.
4. Add `GET /api/assistant/quota`.
5. Add parsers/unit tests and basic monitoring.

---

## 10. Cost control, monitoring, and safety

Cost control:

- Log and aggregate token usage per user/day.
- Provide admin alerts on spending spikes.

Monitoring:

- Export metrics (requests, errors, latency, parse failures, quota denials).

Safety:

- Validate AI JSON outputs; do not accept unvalidated model outputs as truth without checks.

---

## 11. Assistant quota (refined)

Reminder: keep `weekly_ai_turn` in `feedback` unchanged. Assistant uses separate `AssistantQuota`.

Model (OneToOne with `accounts.User`): `limit`, `used`, `period_seconds`, `period_start`, `created_at`, `updated_at`.

Reservation semantics (recommended):

- Start transaction, `select_for_update()` quota row, if period expired reset used, if used + amount <= limit then increment used and proceed. On model failure rollback.

Helper API: `get_or_create_quota(user)` and `check_and_consume_quota(user, amount=1, reserve=True)`.

Expose `GET /api/assistant/quota` and return `{ remaining, limit, reset_at }`.

Rollout:

- Option A: add quota defaults per role and do not migrate `weekly_ai_turn`.
- Option B: optional migration script to import existing turns into `AssistantQuota`.

---

## 12. Tests & rollout checklist

- Unit tests for quota concurrency and parsers.
- Integration tests for end-to-end flow (reserve, call, success/failure).
- Staging rollout with low limits and monitoring of costs and parse errors.

---

## 13. Next steps

I can generate a code patch that implements:

1. `assistant` app with `AssistantQuota` model and migration.
2. `assistant/utils.py` with `check_and_consume_quota` and AI wrapper.
3. `POST /api/assistant/conversations/{id}/messages` view + serializer using existing auth.
4. Unit tests for quota and parsing.

Choose: `apply` (I will create and run the changes) or `preview` (I will produce the patch for your review).
