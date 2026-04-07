-- Seed data for class CompletedBonus
-- This file is executed after Django migrations in entrypoint.sh

INSERT INTO completed_bonus (skill, level, completed_bonus)
VALUES
--Reading
('R', 'A1', 15),
('R', 'A2', 20),
('R', 'B1', 25),
('R', 'B2', 30),
--Listening
('L', 'A1', 10),
('L', 'A2', 15),
('L', 'B1', 20),
('L', 'B2', 25),
--Writing
('W', 'A1', 45),
('W', 'A2', 50),
('W', 'B1', 55),
('W', 'B2', 60),
--Speaking
('S', 'A1', 40),
('S', 'A2', 45),
('S', 'B1', 50),
('S', 'B2', 55)
ON CONFLICT (skill, level) DO NOTHING;