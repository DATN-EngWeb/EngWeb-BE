-- Seed data for teachers
-- This file initializes sample teachers from sample_users.csv
-- Run this after seeding users

INSERT INTO teacher (
    user_id,
    current_workplace,
    teacher_type,
    experience_year,
    introduction,
    credentials,
    created_at,
    updated_at,
    weekly_ai_turn
) VALUES
(1015, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-16 10:00:00+00', '2024-01-16 10:00:00+00', 2),
(1016, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-17 10:00:00+00', '2024-01-17 10:00:00+00', 2),
(1017, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-18 10:00:00+00', '2024-01-18 10:00:00+00', 2),
(1018, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-19 10:00:00+00', '2024-01-19 10:00:00+00', 2),
(1019, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-20 10:00:00+00', '2024-01-20 10:00:00+00', 2),
(1020, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-21 10:00:00+00', '2024-01-21 10:00:00+00', 2),
(1021, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-22 10:00:00+00', '2024-01-22 10:00:00+00', 2),
(1022, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-23 10:00:00+00', '2024-01-23 10:00:00+00', 2),
(1023, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-24 10:00:00+00', '2024-01-24 10:00:00+00', 2),
(1024, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-25 10:00:00+00', '2024-01-25 10:00:00+00', 2),
(1025, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-26 10:00:00+00', '2024-01-26 10:00:00+00', 2),
(1026, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-27 10:00:00+00', '2024-01-27 10:00:00+00', 2),
(1027, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-28 10:00:00+00', '2024-01-28 10:00:00+00', 2),
(1028, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-29 10:00:00+00', '2024-01-29 10:00:00+00', 2),
(1029, 'School ABC', 'F', 5, 'Experienced teacher', '{}'::jsonb, '2024-01-30 10:00:00+00', '2024-01-30 10:00:00+00', 2)
ON CONFLICT (user_id) DO NOTHING;