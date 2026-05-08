-- Seed data for EXPBonusRule model
-- This file is executed after Django migrations in entrypoint.sh
-- Intervals are half-open [min, max) except for the last one which includes 100%

INSERT INTO exp_bonus_rule (min_percentage, max_percentage, exp_percentage, rating, feedback_message)
VALUES
-- Try again: 0-49%
(0, 50, 0, 'Try again', '💡 No worries. Everyone starts somewhere. Review the lesson and give it another try!'),

-- Needs improvement: 50-59%
(50, 60, 40, 'Needs improvement', '⚠️ Keep going! You are getting close. Check the feedback and practice a bit more!'),

-- Pass: 60-69%
(60, 70, 60, 'Pass', '📈 Nice effort! Read through the feedback and try one more time!'),

-- Fair: 70-79%
(70, 80, 80, 'Fair', '💪 Good job! You are almost there. Keep pushing!'),

-- Good: 80-89%
(80, 90, 100, 'Good', '👏 Well done! You have a solid grasp of this test!'),

-- Excellent: 90-100%
(90, 100, 120, 'Excellent', '🎉 Excellent work! You did a fantastic job. Keep it up!')

ON CONFLICT (min_percentage, max_percentage) DO NOTHING;
