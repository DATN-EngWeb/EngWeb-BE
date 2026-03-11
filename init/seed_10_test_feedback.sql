-- Seed data for test feedback
-- Run this after seeding tests and users
-- Initializes sample feedback for Tests 1, 2, 3, and 4

INSERT INTO test_feedback (
    test_id,
    teacher_id,
    comment,
    created_at,
    updated_at,
    created_by
) VALUES
-- Feedback for Test 1 (Receptive: Reading - A1)
(1, NULL, 'The reading passage about coffee is well-structured and highly engaging for A1 learners.', '2026-03-01 10:00:00+00', '2026-03-01 10:00:00+00', 'A'),
(1, 1024, 'I agree with the AI, but perhaps question 3 needs simpler vocabulary options.', '2026-03-02 11:30:00+00', '2026-03-02 11:30:00+00', 'T'),
(1, 1025, 'Great use of visuals in Part 1. It helps beginners grasp the context quickly.', '2026-03-03 09:15:00+00', '2026-03-03 09:15:00+00', 'T'),
(1, 1026, 'The time limit of 3 minutes is a bit tight for A1. Consider increasing it to 5 minutes.', '2026-03-04 14:20:00+00', '2026-03-04 14:20:00+00', 'T'),
(1, 1015, 'I will use this test structure for my next beginner class. Very inspiring.', '2026-03-05 16:45:00+00', '2026-03-05 16:45:00+00', 'T'),

-- Feedback for Test 2 (Productive: Writing - B1)
(2, NULL, 'The writing prompt requires B1-level argumentation. The glue text effectively bridges the tasks.', '2026-02-15 08:30:00+00', '2026-02-15 08:30:00+00', 'A'),
(2, 1024, '250 words might be a stretch for some B1 students. Maybe lower the minimum word count to 200?', '2026-02-16 10:55:00+00', '2026-02-16 10:55:00+00', 'T'),
(2, 1025, 'The topic is relevant, but the description is slightly vague. Could use more bullet points.', '2026-02-17 13:10:00+00', '2026-02-17 13:10:00+00', 'T'),
(2, 1016, 'I love the format! Students usually struggle with this type of essay, so this is great practice.', '2026-02-18 09:25:00+00', '2026-02-18 09:25:00+00', 'T'),
(2, 1017, 'Can we add a sample answer for this test to guide the students?', '2026-02-19 15:40:00+00', '2026-02-19 15:40:00+00', 'T'),

-- Feedback for Test 3 (Productive: Writing an email - B1)
(3, NULL, 'This informal email task aligns perfectly with B1 Cambridge exam specifications.', '2026-02-20 11:00:00+00', '2026-02-20 11:00:00+00', 'A'),
(3, 1024, 'The 100-word limit is spot on. It forces students to be concise.', '2026-02-21 14:30:00+00', '2026-02-21 14:30:00+00', 'T'),
(3, 1025, 'I noticed a typo in the prompt image. Can the author update the resource?', '2026-02-22 10:15:00+00', '2026-02-22 10:15:00+00', 'T'),
(3, 1026, 'Excellent test. My students really engaged with the "birthday meal" scenario.', '2026-02-23 16:20:00+00', '2026-02-23 16:20:00+00', 'T'),
(3, 1018, 'The time limit of 30 minutes gives them plenty of time to plan and review. Good job.', '2026-02-24 09:50:00+00', '2026-02-24 09:50:00+00', 'T'),

-- Feedback for Test 4 (Productive: Speaking - A2)
(4, NULL, 'The speaking topic "Places to eat" is highly relatable and suitable for A2 fluency development.', '2026-03-06 08:45:00+00', '2026-03-06 08:45:00+00', 'A'),
(4, 1024, 'I think adding an audio example would help A2 students understand the expected pronunciation.', '2026-03-07 11:10:00+00', '2026-03-07 11:10:00+00', 'T'),
(4, 1025, 'The 30-minute duration is too long for an A2 speaking task. Consider breaking it down into 3 shorter parts.', '2026-03-08 14:35:00+00', '2026-03-08 14:35:00+00', 'T'),
(4, 1026, 'Great topic! I will assign this as homework for my conversational class tonight.', '2026-03-09 10:05:00+00', '2026-03-09 10:05:00+00', 'T'),
(4, 1019, 'The description perfectly explains what the student needs to describe. Very clear instructions.', '2026-03-10 15:55:00+00', '2026-03-10 15:55:00+00', 'T')
ON CONFLICT (id) DO NOTHING;
