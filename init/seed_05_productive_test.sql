-- Seed data for Productive Test
-- This file initializes sample data for a Productive Test (Writing type)
-- Run this after creating the database schema

-- Insert into test table
INSERT INTO test (id, title, type, level, skill, time, description, status, created_at, updated_at, created_by_id) VALUES
(2, 'productive test', 'P', 'B1', 'W', 60, 'description of productive test', 'D', '2026-01-21 04:16:47.998+00', '2026-01-21 04:16:47.998+00', 1024);

-- Insert into productive_test table
INSERT INTO productive_test (test_id, format, topic, description, min_word, glue_text, glue_resources) VALUES
(2, 'A', 'topic of productive test', 'https://example.com/media/tests/2/part1/content.html', 250, 'glue text', '{}'::jsonb);