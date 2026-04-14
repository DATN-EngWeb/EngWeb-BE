-- Seed data for UserLevel model
-- This file is executed after Django migrations in entrypoint.sh

INSERT INTO user_level (level_number, level_title, level_icon, min_xp, max_xp)
VALUES
(1, 'Rookie', 'https://cdn.jsdelivr.net/npm/@tabler/icons/icons/star.svg', 0, 100),
(2, 'Beginner', 'https://cdn.jsdelivr.net/npm/@tabler/icons/icons/book.svg', 100, 250),
(3, 'Apprentice', 'https://cdn.jsdelivr.net/npm/@tabler/icons/icons/pencil.svg', 250, 500),
(4, 'Learner', 'https://cdn.jsdelivr.net/npm/@tabler/icons/icons/target.svg', 500, 900),
(5, 'Skilled', 'https://cdn.jsdelivr.net/npm/@tabler/icons/icons/bolt.svg', 900, 1400),
(6, 'Advanced', 'https://cdn.jsdelivr.net/npm/@tabler/icons/icons/rocket.svg', 1400, 1900),
(7, 'Expert', 'https://cdn.jsdelivr.net/npm/@tabler/icons/icons/trophy.svg', 1900, 2400),
(8, 'Master', 'https://cdn.jsdelivr.net/npm/@tabler/icons/icons/crown.svg', 2400, 999999)
ON CONFLICT (level_number) DO NOTHING;