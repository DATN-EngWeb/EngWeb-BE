-- Seed data for students
-- This file initializes sample students from sample_users.csv
-- Run this after seeding users

INSERT INTO student (user_id, cumulative_point, weekly_point, weekly_ai_turn, bonus_ai_turn, completed_test, qualified_test, last_submitted_date, streak_count, max_streak, level_id, created_at, updated_at) VALUES
(1006, 0, 0, 4, 0, 0, 0, NULL, 0, 0, 1, '2024-01-07 10:00:00+00', '2024-01-07 10:00:00+00'),
(1007, 0, 0, 4, 0, 0, 0, NULL, 0, 0, 1, '2024-01-08 10:00:00+00', '2024-01-08 10:00:00+00'),
(1008, 0, 0, 4, 0, 0, 0, NULL, 0, 0, 1, '2024-01-09 10:00:00+00', '2024-01-09 10:00:00+00'),
(1009, 0, 0, 4, 0, 0, 0, NULL, 0, 0, 1, '2024-01-10 10:00:00+00', '2024-01-10 10:00:00+00'),
(1010, 0, 0, 4, 0, 0, 0, NULL, 0, 0, 1, '2024-01-11 10:00:00+00', '2024-01-11 10:00:00+00'),
(1011, 0, 0, 4, 0, 0, 0, NULL, 0, 0, 1, '2024-01-12 10:00:00+00', '2024-01-12 10:00:00+00'),
(1012, 0, 0, 4, 0, 0, 0, NULL, 0, 0, 1, '2024-01-13 10:00:00+00', '2024-01-13 10:00:00+00'),
(1013, 0, 0, 4, 0, 0, 0, NULL, 0, 0, 1, '2024-01-14 10:00:00+00', '2024-01-14 10:00:00+00'),
(1014, 0, 0, 4, 0, 0, 0, NULL, 0, 0, 1, '2024-01-15 10:00:00+00', '2024-01-15 10:00:00+00')
ON CONFLICT (user_id) DO NOTHING;