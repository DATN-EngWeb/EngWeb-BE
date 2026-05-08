-- Seed data for SpeakingCriteriaTemplate
-- This file is executed after Django migrations in entrypoint.sh

INSERT INTO speaking_criteria_template (
    level,
    band,
    grammar_and_vocabulary,
    discourse_management,
    pronunciation,
    task_achievement
)
VALUES
-- A2 Level
('A2', 0, 'Performance below Band 1.', 'Performance below Band 1.', 'Performance below Band 1.', 'Content is totally irrelevant. Target reader is not informed.'),
('A2', 1, 'Shows only limited control of a few grammatical forms. Uses a vocabulary of isolated words and phrases.', 'Produces responses which are characterised by short phrases and frequent hesitation. Repeats information or digresses from the topic.', 'Has very limited control of phonological features and is often unintelligible.', 'Irrelevances and misinterpretation of task may be present. Target reader is minimally informed.'),
('A2', 2, 'Performance shares features of Bands 1 and 3.', 'Performance shares features of Bands 1 and 3.', 'Performance shares features of Bands 1 and 3.', 'Performance shares features of Bands 1 and 3'),
('A2', 3, 'Shows sufficient control of simple grammatical forms. Uses appropriate vocabulary to talk about everyday situations.', 'Produces responses which are extended beyond short phrases, despite hesitation. Contributions are mostly relevant, but there may be some repetition. Uses basic cohesive devices.', 'Is mostly intelligible, despite limited control of phonological features.', 'Minor irrelevances and/or omissions may be present. Target reader is on the whole informed.'),
('A2', 4, 'Performance shares features of Bands 3 and 5.', 'Performance shares features of Bands 3 and 5.', 'Performance shares features of Bands 3 and 5.', 'Performance shares features of Bands 3 and 5'),
('A2', 5, 'Shows a good degree of control of simple grammatical forms. Uses a range of appropriate vocabulary when talking about everyday situations.', 'Produces extended stretches of language despite some hesitation. Contributions are relevant despite some repetition. Uses a range of cohesive devices.', 'Is mostly intelligible, and has some control of phonological features at both utterance and word levels.', 'All content is relevant to the task. Target reader is fully informed.'),
-- B1 Level
('B1', 0, 'Performance below Band 1.', 'Performance below Band 1.', 'Performance below Band 1.', 'Content is totally irrelevant. Target reader is not informed.'),
('B1', 1, 'Shows sufficient control of simple grammatical forms. Uses a limited range of appropriate vocabulary to talk about familiar topics.', 'Produces responses which are characterised by short phrases and frequent hesitation. Repeats information or digresses from the topic.', 'Is mostly intelligible, despite limited control of phonological features.', 'Irrelevances and misinterpretation of task may be present. Target reader is minimally informed'),
('B1', 2, 'Performance shares features of Bands 1 and 3.', 'Performance shares features of Bands 1 and 3.', 'Performance shares features of Bands 1 and 3.', 'Performance shares features of Bands 1 and 3'),
('B1', 3, 'Shows a good degree of control of simple grammatical forms. Uses a range of appropriate vocabulary when talking about familiar topics.', 'Produces responses which are extended beyond short phrases, despite hesitation. Contributions are mostly relevant, but there may be some repetition. Uses basic cohesive devices.', 'Is mostly intelligible, and has some control of phonological features at both utterance and word levels.', 'Minor irrelevances and/or omissions may be present. Target reader is on the whole informed.'),
('B1', 4, 'Performance shares features of Bands 3 and 5.', 'Performance shares features of Bands 3 and 5.', 'Performance shares features of Bands 3 and 5.', 'Performance shares features of Bands 3 and 5.'),
('B1', 5, 'Shows a good degree of control of simple grammatical forms, and attempts some complex grammatical forms. Uses a range of appropriate vocabulary to give and exchange views on familiar topics.', 'Produces extended stretches of language despite some hesitation. Contributions are relevant despite some repetition. Uses a range of cohesive devices.', 'Is intelligible. Intonation is generally appropriate. Sentence and word stress is generally accurately placed. Individual sounds are generally articulated clearly.', 'All content is relevant to the task. Target reader is fully informed'),
-- B2 Level
('B2', 0, 'Performance below Band 1.', 'Performance below Band 1.', 'Performance below Band 1.', 'Content is totally irrelevant. Target reader is not informed.'),
('B2', 1, 'Shows a good degree of control of simple grammatical forms. Uses a range of appropriate vocabulary when talking about everyday situations.', 'Produces responses which are extended beyond short phrases, despite hesitation. Contributions are mostly relevant, despite some repetition. Uses basic cohesive devices.', 'Is mostly intelligible, and has some control of phonological features at both utterance and word levels.', 'Irrelevances and misinterpretation of task may be present. Target reader is minimally informed.'),
('B2', 2, 'Performance shares features of Bands 1 and 3.', 'Performance shares features of Bands 1 and 3.', 'Performance shares features of Bands 1 and 3.', 'Performance shares features of Bands 1 and 3'),
('B2', 3, 'Shows a good degree of control of simple grammatical forms, and attempts some complex grammatical forms. Uses a range of appropriate vocabulary to give and exchange views on a range of familiar topics.', 'Produces extended stretches of language despite some hesitation. Contributions are relevant and there is very little repetition. Uses a range of cohesive devices.', 'Is intelligible. Intonation is generally appropriate. Sentence and word stress is generally accurately placed. Individual sounds are generally articulated clearly.', 'Minor irrelevances and/or omissions may be present. Target reader is on the whole informed.'),
('B2', 4, 'Performance shares features of Bands 3 and 5.', 'Performance shares features of Bands 3 and 5.', 'Performance shares features of Bands 3 and 5.', 'Performance shares features of Bands 3 and 5.'),
('B2', 5, 'Shows a good degree of control of a range of simple and some complex grammatical forms. Uses a range of appropriate vocabulary to give and exchange views on a wide range of familiar topics.', 'Produces extended stretches of language with very little hesitation. Contributions are relevant and there is a clear organisation of ideas. Uses a range of cohesive devices and discourse markers.', 'Is intelligible. Intonation is appropriate. Sentence and word stress is accurately placed. Individual sounds are articulated clearly.', 'All content is relevant to the task. Target reader is fully informed.')
ON CONFLICT (level, band) DO NOTHING;

