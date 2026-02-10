-- Seed data for Productive Test
-- This file initializes sample data for a Productive Test (Writing type)
-- Run this after creating the database schema

-- Seed data for Productive Test (Added ID 3)

-- Insert into test table
INSERT INTO test (id, title, level, skill, time, description, status, created_at, updated_at, created_by_id, type) VALUES
(2, 'productive test', 'B1', 'W', 60, 'description of productive test', 'D', '2026-01-21 04:16:47.998+00', '2026-01-21 04:16:47.998+00', 1024, 'P'),
(3, 'Write an email', 'B1', 'W', 30, 'Writing test', 'I', '2026-02-05 14:56:44.913668+00', '2026-02-05 14:56:44.913681+00', 1024, 'P')
ON CONFLICT (id) DO NOTHING;

-- Insert into productive_test table
INSERT INTO productive_test (test_id, format, topic, description, min_word, glue_text, glue_resources) VALUES
(2, 'A', 'topic of productive test', 'https://example.com/media/tests/2/part1/content.html', 250, 'glue text', '{}'::jsonb),
(3, 'A', 'Email', 'https://storage.googleapis.com/dev-nens-english-app-test-vu/media/tests/3/part1/5e9c09a2-5f6c-4a17-8807-8dc00cbe9d8a.html', 100, '', '{"audio": null, "image": null}'::jsonb)
ON CONFLICT (test_id) DO NOTHING;