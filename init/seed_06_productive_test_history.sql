-- Seed data for Productive Test History (Writing/Speaking submissions)
-- This file creates sample history submissions for 2 students for Productive Test ID = 3
-- Run this after:
--   - seed_01_users.sql / seed_03_student.sql (students exist)
--   - seed_05_productive_test.sql (productive test exists)

INSERT INTO productive_test_history (
    student_id,
    productive_test_id,
    attempt,
    type,
    start_time,
    end_time,
    total_time,
    audio_path,
    user_answer_text,
    user_note_text,
    ai_feedback,
    earned_bonus_point
) VALUES
(
    1009,
    3,
    1,
    'S',
    '2026-02-07 10:00:00+00',
    '2026-02-07 10:17:30+00',
    1050,
    NULL,
    'Hello Robbie\n\n\n\nThank you for your email! I\u2019m so glad that you will celebrate your birthday in a restuarant. I think it\u2019s a really cool idea, because it will be a really memorible birthday.\n\nAlso about the restuarants. I recomend the we should go in a burger restuarant, because everyone loves burgers and fastfood. It will be grateful if you will pick me up to the restuarant. My parents are always at work, so I don\u2019t think they can take me to the restuarant.\n\nAlso I\u2019ve got a question to ask you. Should we go to the restuarant in street clothes or we all need to be properly dressed? I hope you will answer me soone.\n\nYour friend\n\nDima',
    NULL,
    NULL,
    0
),
(
    1010,
    3,
    1,
    'S',
    '2026-02-07 11:00:00+00',
    '2026-02-07 11:14:10+00',
    850,
    NULL,
    'Hello First I want to wish you a happy birthday! And thanks for the invitation, I would love to come. I think its a really good idea to have more people, because with more people there will be more fun, plus people can meet each other and make new friends.\n\n\n\nPersonaly I think you should host the party in the first restuarant, people will have a wider range of options, plus there might be a vegan menu\n\nThanks for asking I would like for you to pick me up, because I don\u2019t have a car.\n\nAnd one more thing. Can you tell me if I have to dress specificly for the party?\n\nDaniel',
    NULL,
    NULL,
    0
),
-- Speaking submissions for Productive Test ID = 4 (Places to eat)
(
    1009,
    4,
    1,
    'S',
    '2026-03-03 15:51:42.286+00',
    '2026-03-03 15:53:36.732+00',
    114,
    'https://storage.googleapis.com/dev-nens-english-app-test-vu/tests/test_4/756f3f7a-4ef5-4084-b40a-1b19fe6c8737.webm',
    NULL,
    NULL,
    0
),
(
    1010,
    4,
    1,
    'S',
    '2026-03-03 15:54:17.752+00',
    '2026-03-03 15:54:29.246+00',
    11,
    'https://storage.googleapis.com/dev-nens-english-app-test-vu/tests/test_4/6c96222c-78fc-4f30-bfdc-d760f3d07752.webm',
    NULL,
    NULL,
    0
)
ON CONFLICT (student_id, productive_test_id, attempt) DO NOTHING;

