-- Seed data for EXPBonusRule model
-- This file is executed after Django migrations in entrypoint.sh
-- Intervals are half-open [min, max) except for the last one which includes 100%

INSERT INTO exp_bonus_rule (min_percentage, max_percentage, exp_percentage, rating, feedback_message)
VALUES
-- Try again: 0-49%
(0, 50, 0, 'Try again', '💡 Chưa sao! Mọi người đều phải học từ đầu. Xem lại bài học và thử lại nhé!'),

-- Needs improvement: 50-59%
(50, 60, 40, 'Needs improvement', '⚠️ Cố lên! Bạn sắp tốt rồi đấy. Hãy xem lại feedback và luyện tập thêm!'),

-- Pass: 60-69%
(60, 70, 60, 'Pass', '📈 Bạn đã cố gắng! Đọc lại feedback và thử lại nhé!'),

-- Fair: 70-79%
(70, 80, 80, 'Fair', '💪 Khá tốt! Còn một chút nữa thôi, cố lên!'),

-- Good: 80-89%
(80, 90, 100, 'Good', '👏 Tốt lắm! Bạn đã nắm vững bài này rồi!'),

-- Excellent: 90-100%
(90, 100, 120, 'Excellent', '🎉 Xuất sắc! Bạn đã làm rất tốt! Tiếp tục phát huy nhé!')

ON CONFLICT DO NOTHING;
