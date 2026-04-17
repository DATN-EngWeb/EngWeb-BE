INSERT INTO notification (
    user_id,
    type,
    title,
    content,
    reference_id,
    is_read,
    created_at
) VALUES

-- ============================================================
-- TYPE 'C' — Comment notifications (30 records)
-- ============================================================

-- POST 1 (owner: user 1009 = student4, status=V)
-- 10 comments from users 1000-1009
(1009, 'C', 'admin1 commented on your post.', 'Great writing submission, the vocabulary is decent.', 1,  true,  '2026-02-07 10:25:00+00'),
(1009, 'C', 'admin2 commented on your post.', 'I think you can try to write more complex sentences.', 2,  true,  '2026-02-07 10:30:00+00'),
(1009, 'C', 'admin3 commented on your post.', 'Very clear structure, keep it up!', 3,               true,  '2026-02-07 10:45:00+00'),
(1009, 'C', 'admin4 commented on your post.', 'This is a difficult topic but you handled it well.', 4, true, '2026-02-07 11:00:00+00'),
(1009, 'C', 'admin5 commented on your post.', 'Watch out for spelling mistakes in the conclusion.', 5,   true,  '2026-02-07 11:15:00+00'),
(1009, 'C', 'admin6 commented on your post.', 'Nice use of transition words.', 6,                    true,  '2026-02-07 11:30:00+00'),
(1009, 'C', 'student1 commented on your post.', 'I would score this a B2 level.', 7,                false, '2026-02-07 12:00:00+00'),
(1009, 'C', 'student2 commented on your post.', 'Do you have any tips for writing this fast?', 8,     false, '2026-02-07 12:30:00+00'),
(1009, 'C', 'student3 commented on your post.', 'The introduction is a bit too short.', 9,           false, '2026-02-07 13:00:00+00'),
(1009, 'C', 'student4 commented on your post.', 'Thanks for sharing your work!', 10,                 false, '2026-02-07 13:30:00+00'),

-- POST 2 (owner: user 1009 = student4, status=V)
-- 8 comments from users 1010-1017 (student5-student12)
(1009, 'C', 'student5 commented on your post.', 'Your vocabulary is fine, don''t worry!', 11,                         false, '2026-02-07 11:35:00+00'),
(1009, 'C', 'student6 commented on your post.', 'Try reading more articles to improve your lexical resource.', 12,       false, '2026-02-07 11:40:00+00'),
(1009, 'C', 'student7 commented on your post.', 'I love how you organized the paragraphs.', 13,                          false, '2026-02-07 11:50:00+00'),
(1009, 'C', 'student8 commented on your post.', 'Some grammatical errors here and there, but overall good.', 14,        false, '2026-02-07 12:10:00+00'),
(1009, 'C', 'student9 commented on your post.', 'What time did it take you to finish this?', 15,                         false, '2026-02-07 12:45:00+00'),
(1009, 'C', 'teacher1 commented on your post.', 'Very inspiring submission.', 16,                                           false, '2026-02-07 13:15:00+00'),
(1009, 'C', 'teacher2 commented on your post.', 'Could be better if you added more examples.', 17,                       false, '2026-02-07 13:40:00+00'),
(1009, 'C', 'teacher3 commented on your post.', 'Great effort nonetheless.', 18,                                          false, '2026-02-07 14:00:00+00'),

-- POST 3 (owner: user 1010 = student5, status=V)
-- 7 comments from users 1018-1024 (teacher4-teacher10)
(1010, 'C', 'teacher4 commented on your post.', 'Your pronunciation is so clear!', 19,                    false, '2026-03-03 16:15:00+00'),
(1010, 'C', 'teacher5 commented on your post.', 'Very natural fluency, sounds like a native.', 20,         false, '2026-03-03 16:30:00+00'),
(1010, 'C', 'teacher6 commented on your post.', 'Awesome job.', 21,                                      false, '2026-03-03 16:45:00+00'),
(1010, 'C', 'teacher7 commented on your post.', 'Try to avoid using too many fillers like "um" or "uh".', 22, false, '2026-03-03 17:00:00+00'),
(1010, 'C', 'teacher8 commented on your post.', 'Intonation could use a little bit of work.', 23,         false, '2026-03-03 17:15:00+00'),
(1010, 'C', 'teacher9 commented on your post.', 'Excellent vocabulary for a speaking test.', 24,           false, '2026-03-03 17:30:00+00'),
(1010, 'C', 'teacher10 commented on your post.', 'Nice answers!', 25,                                     false, '2026-03-03 17:45:00+00'),

-- POST 4 (owner: user 1010 = student5, status=V)
-- 5 comments from users 1025-1029 (teacher11-teacher15)
(1010, 'C', 'teacher11 commented on your post.', 'It is indeed very short.', 26,                              false, '2026-03-03 16:10:00+00'),
(1010, 'C', 'teacher12 commented on your post.', 'Short but straight to the point.', 27,                    false, '2026-03-03 16:20:00+00'),
(1010, 'C', 'teacher13 commented on your post.', 'You missed the second part of the question.', 28,          false, '2026-03-03 16:35:00+00'),
(1010, 'C', 'teacher14 commented on your post.', 'Don''t worry, practice makes perfect.', 29,                false, '2026-03-03 16:50:00+00'),
(1010, 'C', 'teacher15 commented on your post.', 'Keep trying, you will get better next time!', 30,          false, '2026-03-03 17:05:00+00'),

-- ============================================================
-- TYPE 'F' — Feedback notifications (12 records)
-- Only for teacher10 (1024, status=V) — tests 2, 3, 4
-- Test 1 excluded (owner teacher1=1015, status=P != V)
-- ============================================================

-- TEST 2 (id=2, created_by=1024 = teacher10, status=V): feedback 7-10 (teacher_id is set)
(1024, 'F', 'teacher11 left feedback on your test.', 'The topic is relevant, but the description is slightly vague. Could use more bullet points.', 8,  false, '2026-02-17 13:10:00+00'),
(1024, 'F', 'teacher2 left feedback on your test.', 'I love the format! Students usually struggle with this type of essay, so this is great practice.', 9, false, '2026-02-18 09:25:00+00'),
(1024, 'F', 'teacher3 left feedback on your test.', 'Can we add a sample answer for this test to guide the students?', 10, false, '2026-02-19 15:40:00+00'),

-- TEST 3 (id=3, created_by=1024 = teacher10, status=V): feedback 12-15 (teacher_id is set)
(1024, 'F', 'teacher11 left feedback on your test.', 'I noticed a typo in the prompt image. Can the author update the resource?', 13, false, '2026-02-22 10:15:00+00'),
(1024, 'F', 'teacher12 left feedback on your test.', 'Excellent test. My students really engaged with the "birthday meal" scenario.', 14, false, '2026-02-23 16:20:00+00'),
(1024, 'F', 'teacher4 left feedback on your test.', 'The time limit of 30 minutes gives them plenty of time to plan and review. Good job.', 15, false, '2026-02-24 09:50:00+00'),

-- TEST 4 (id=4, created_by=1024 = teacher10, status=V): feedback 17-20 (teacher_id is set)
(1024, 'F', 'teacher11 left feedback on your test.', 'The 30-minute duration is too long for an A2 speaking task. Consider breaking it down into 3 shorter parts.', 18, false, '2026-03-08 14:35:00+00'),
(1024, 'F', 'teacher12 left feedback on your test.', 'Great topic! I will assign this as homework for my conversational class tonight.', 19, false, '2026-03-09 10:05:00+00'),
(1024, 'F', 'teacher5 left feedback on your test.', 'The description perfectly explains what the student needs to describe. Very clear instructions.', 20, false, '2026-03-10 15:55:00+00')

ON CONFLICT DO NOTHING;
