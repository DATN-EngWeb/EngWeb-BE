-- Seed data for StreakRewardRule model
-- This file is executed after Django migrations in entrypoint.sh

INSERT INTO streak_reward_rule (streak_day, xp_reward, ai_turn_reward)
VALUES
(3, 20, 1),
(7, 50, 3),
(14, 100, 5),
(30, 200, 10),
(100, 400, 15)
ON CONFLICT (streak_day) DO NOTHING;
