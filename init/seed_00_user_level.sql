-- Seed data for UserLevel model
-- This file is executed after Django migrations in entrypoint.sh

INSERT INTO user_level (id, level_number, level_title, min_xp, max_xp)
VALUES
(1, 1, 'Newbie', 0, 299),
(2, 2, 'Learner', 300, 699),
(3, 3, 'Student', 700, 1199),
(4, 4, 'Practitioner', 1200, 1999),
(5, 5, 'Intermediate', 2000, 3199),
(6, 6, 'Upper-Intermediate', 3200, 4999),
(7, 7, 'Advanced', 5000, 7499),
(8, 8, 'Proficient', 7500, 10999),
(9, 9, 'Expert', 11000, 15999),
(10, 10, 'Master', 16000, 24999)
ON CONFLICT (level_number) DO NOTHING;

-- Update sequence after seeding explicit IDs
SELECT setval('user_level_id_seq', (SELECT COALESCE(MAX(id), 1) FROM user_level));