-- Seed data for Post Comments
-- Distributes 30 comments across 4 posts: 
-- 10 comments for Post 1
-- 8 comments for Post 2
-- 7 comments for Post 3
-- 5 comments for Post 4

INSERT INTO post_comment (
    id,
    content,
    created_at,
    updated_at,
    post_id,
    user_id
) VALUES
-- Post 1 Comments (10 users: 1000 - 1009)
(1, 'Great writing submission, the vocabulary is decent.', '2026-02-07 10:25:00+00', '2026-02-07 10:25:00+00', 1, 1000),
(2, 'I think you can try to write more complex sentences.', '2026-02-07 10:30:00+00', '2026-02-07 10:30:00+00', 1, 1001),
(3, 'Very clear structure, keep it up!', '2026-02-07 10:45:00+00', '2026-02-07 10:45:00+00', 1, 1002),
(4, 'This is a difficult topic but you handled it well.', '2026-02-07 11:00:00+00', '2026-02-07 11:00:00+00', 1, 1003),
(5, 'Watch out for spelling mistakes in the conclusion.', '2026-02-07 11:15:00+00', '2026-02-07 11:15:00+00', 1, 1004),
(6, 'Nice use of transition words.', '2026-02-07 11:30:00+00', '2026-02-07 11:30:00+00', 1, 1005),
(7, 'I would score this a B2 level.', '2026-02-07 12:00:00+00', '2026-02-07 12:00:00+00', 1, 1006),
(8, 'Do you have any tips for writing this fast?', '2026-02-07 12:30:00+00', '2026-02-07 12:30:00+00', 1, 1007),
(9, 'The introduction is a bit too short.', '2026-02-07 13:00:00+00', '2026-02-07 13:00:00+00', 1, 1008),
(10, 'Thanks for sharing your work!', '2026-02-07 13:30:00+00', '2026-02-07 13:30:00+00', 1, 1009),

-- Post 2 Comments (8 users: 1010 - 1017)
(11, 'Your vocabulary is fine, don''t worry!', '2026-02-07 11:35:00+00', '2026-02-07 11:35:00+00', 2, 1010),
(12, 'Try reading more articles to improve your lexical resource.', '2026-02-07 11:40:00+00', '2026-02-07 11:40:00+00', 2, 1011),
(13, 'I love how you organized the paragraphs.', '2026-02-07 11:50:00+00', '2026-02-07 11:50:00+00', 2, 1012),
(14, 'Some grammatical errors here and there, but overall good.', '2026-02-07 12:10:00+00', '2026-02-07 12:10:00+00', 2, 1013),
(15, 'What time did it take you to finish this?', '2026-02-07 12:45:00+00', '2026-02-07 12:45:00+00', 2, 1014),
(16, 'Very inspiring submission.', '2026-02-07 13:15:00+00', '2026-02-07 13:15:00+00', 2, 1015),
(17, 'Could be better if you added more examples.', '2026-02-07 13:40:00+00', '2026-02-07 13:40:00+00', 2, 1016),
(18, 'Great effort nonetheless.', '2026-02-07 14:00:00+00', '2026-02-07 14:00:00+00', 2, 1017),

-- Post 3 Comments (7 users: 1018 - 1024)
(19, 'Your pronunciation is so clear!', '2026-03-03 16:15:00+00', '2026-03-03 16:15:00+00', 3, 1018),
(20, 'Very natural fluency, sounds like a native.', '2026-03-03 16:30:00+00', '2026-03-03 16:30:00+00', 3, 1019),
(21, 'Awesome job.', '2026-03-03 16:45:00+00', '2026-03-03 16:45:00+00', 3, 1020),
(22, 'Try to avoid using too many fillers like "um" or "uh".', '2026-03-03 17:00:00+00', '2026-03-03 17:00:00+00', 3, 1021),
(23, 'Intonation could use a little bit of work.', '2026-03-03 17:15:00+00', '2026-03-03 17:15:00+00', 3, 1022),
(24, 'Excellent vocabulary for a speaking test.', '2026-03-03 17:30:00+00', '2026-03-03 17:30:00+00', 3, 1023),
(25, 'Nice answers!', '2026-03-03 17:45:00+00', '2026-03-03 17:45:00+00', 3, 1024),

-- Post 4 Comments (5 users: 1025 - 1029)
(26, 'It is indeed very short.', '2026-03-03 16:10:00+00', '2026-03-03 16:10:00+00', 4, 1025),
(27, 'Short but straight to the point.', '2026-03-03 16:20:00+00', '2026-03-03 16:20:00+00', 4, 1026),
(28, 'You missed the second part of the question.', '2026-03-03 16:35:00+00', '2026-03-03 16:35:00+00', 4, 1027),
(29, 'Don''t worry, practice makes perfect.', '2026-03-03 16:50:00+00', '2026-03-03 16:50:00+00', 4, 1028),
(30, 'Keep trying, you will get better next time!', '2026-03-03 17:05:00+00', '2026-03-03 17:05:00+00', 4, 1029)
ON CONFLICT (id) DO NOTHING;

-- Also update the sequence
SELECT setval('post_comment_id_seq', (SELECT COALESCE(MAX(id), 1) FROM post_comment));
