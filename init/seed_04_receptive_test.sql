-- Seed data for Receptive Test
-- This file initializes sample data for a Receptive Test (Reading type)
-- Run this after creating the database schema

-- Insert into test table
INSERT INTO test (id, title, type, level, skill, time, description, status, created_at, updated_at, created_by_id) VALUES
(1, 'aaaa', 'R', 'A1', 'R', 3, 'aaaaaa', 'D', '2026-01-06 15:15:43.261622+07', '2026-01-06 15:15:43.261644+07', 1015);

-- Insert into receptive_test table
INSERT INTO receptive_test (test_id, total_score) VALUES
(1, 20);

-- Insert into receptive_part table
INSERT INTO receptive_part (id, receptive_test_id, "order", format, description, content, score, resources) VALUES
(1, 1, 1, 'F', 'Description of this part', 'https://example.com/media/tests/1/part1/content.html', 10, '{}'::jsonb),
(2, 1, 2, 'F', 'Description of this part', 'https://example.com/media/tests/1/part2/content.html', 10, '{}'::jsonb);

-- Insert into receptive_question table
INSERT INTO receptive_question (id, receptive_part_id, question_number, content, explanation, score, resources) VALUES
(1, 1, 1, 'Question content', 'Explanation for the correct answer', 10, '{"image": "https://example.com/media/tests/1/part1/image1.png"}'::jsonb),
(2, 2, 1, 'Question content', 'Explanation for the correct answer', 10, '{"image": "https://example.com/media/tests/1/part2/image2.png"}'::jsonb);

-- Insert into receptive_answer table
INSERT INTO receptive_answer (id, receptive_question_id, option_label, answer_text, is_correct, resources) VALUES
(1, 1, 'A', 'Option A', true, '{}'::jsonb),
(2, 1, 'B', 'Option B', false, '{}'::jsonb),
(3, 2, 'A', 'Option A', true, '{"image": "https://example.com/media/tests/1/part2/answerA_image.png"}'::jsonb),
(4, 2, 'B', 'Option B', false, '{}'::jsonb);