-- Seed data for Post
-- This file creates 4 sample forum posts for the 4 existing productive test histories

INSERT INTO post (
    id,
    title,
    description,
    like_count,
    comment_count,
    created_at,
    updated_at,
    productive_test_history_id
) VALUES
(
    1,
    'My first Writing Test - Environmental Issues',
    'I found this test extremely difficult, please give me some advice!',
    11,
    10,
    '2026-02-07 10:20:00+00',
    '2026-02-07 10:20:00+00',
    1
),
(
    2,
    'Need feedback on my writing submission',
    'Hello everyone, I just completed this writing test. Is it good enough? I think the vocabulary here could be better.',
    8,
    8,
    '2026-02-07 11:20:00+00',
    '2026-02-07 11:20:00+00',
    2
),
(
    3,
    'Speaking Practice - Places to eat',
    'Hi guys, please rate my pronunciation and fluency! Feel free to leave a comment below.',
    13,
    7,
    '2026-03-03 16:00:00+00',
    '2026-03-03 16:00:00+00',
    3
),
(
    4,
    'Short Speaking test',
    'This was quite short but I hope it is okay. Let me know what you guys think about it.',
    4,
    5,
    '2026-03-03 16:05:00+00',
    '2026-03-03 16:05:00+00',
    4
)
ON CONFLICT (id) DO NOTHING;

-- Also update the sequence
SELECT setval('post_id_seq', (SELECT COALESCE(MAX(id), 1) FROM post));
