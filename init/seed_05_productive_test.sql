-- Seed data for Productive Test
-- This file initializes sample data for Productive Tests (Writing + Speaking)
-- Run this after creating the database schema

-- Insert into test table
INSERT INTO test (id, title, level, skill, time, description, status, created_at, updated_at, created_by_id, type) VALUES
(2, 'productive test', 'B1', 'W', 60, 'description of productive test', 'D', '2026-01-21 04:16:47.998+00', '2026-01-21 04:16:47.998+00', 1024, 'P'),
(3, 'Write an email', 'B1', 'W', 30, 'Writing test', 'I', '2026-02-05 14:56:44.913668+00', '2026-02-05 14:56:44.913681+00', 1024, 'P'),
-- New speaking productive test
(4, 'Places to eat', 'A2', 'S', 30, 'Speaking test', 'P', '2026-03-03 15:31:17.780202+00', '2026-03-03 15:31:17.780214+00', 1024, 'P')
ON CONFLICT (id) DO NOTHING;

-- Insert into productive_test table
INSERT INTO productive_test (test_id, format, topic, description, min_word, glue_text, glue_resources) VALUES
(2, 'A', 'topic of productive test', 'https://example.com/tests/2/part1/content.html', 250, 'glue text', '{}'::jsonb),
(3, 'A', 'Email', 'https://storage.googleapis.com/test-nens-english-app-dev-vu/tests/3/part1/5e9c09a2-5f6c-4a17-8807-8dc00cbe9d8a.html', 100, '', '{"audio": null, "image": null}'::jsonb),
-- Speaking test configuration (format H - Description)
(4, 'H', 'Eating', 'https://storage.googleapis.com/test-nens-english-app-dev-vu/tests/test_4/e9f8c724-8744-4382-92d8-e2cb465a0506.html', 0, '', '{"audio": null, "image": null}'::jsonb)
ON CONFLICT (test_id) DO NOTHING;

-- Update sequence after seeding explicit IDs in test table
SELECT setval('test_id_seq', (SELECT COALESCE(MAX(id), 1) FROM test));