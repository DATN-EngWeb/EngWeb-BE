-- Seed data for ReadingCriteriaTemplate (teacher test-design review rubric)
-- This file is executed after Django migrations in entrypoint.sh

INSERT INTO reading_criteria_template (level, code, name, description, checkpoints, priority)
VALUES
(
    'A1',
    'LEVEL_ALIGNMENT',
    'CEFR Level Alignment',
    'Evaluate whether the test language demand matches A1 beginner-level reading expectations.',
    '["Uses mostly high-frequency everyday vocabulary", "Instructions are short and explicit", "Sentence structures are simple and direct", "Questions do not require advanced inference"]'::jsonb,
    1
),
(
    'A1',
    'PASSAGE_QUALITY',
    'Passage Quality',
    'Evaluate readability, coherence, and suitability of passages for A1 learners.',
    '["Passages are short and focused on one clear topic", "Paragraphing and flow are easy to follow", "No overloaded or abstract wording", "Content is age- and context-appropriate"]'::jsonb,
    2
),
(
    'A1',
    'QUESTION_CLARITY',
    'Question Clarity and Validity',
    'Evaluate whether each question is unambiguous and aligned with the intended reading target.',
    '["Question stems are clear and concise", "No double negatives or confusing wording", "Each item tests one main point", "Correct answer is defensible from passage evidence"]'::jsonb,
    3
),
(
    'A1',
    'DISTRACTOR_QUALITY',
    'Distractor Quality',
    'Evaluate quality of options in multiple-choice tasks.',
    '["Distractors are plausible at A1 level", "No obvious giveaway in grammar or length", "Options are not overlapping or duplicate", "Exactly one best answer exists"]'::jsonb,
    4
),
(
    'A1',
    'SKILL_COVERAGE',
    'Skill Coverage and Balance',
    'Evaluate whether items cover essential beginner reading subskills in a balanced way.',
    '["Includes both gist and detail questions", "Question types are not overly repetitive", "Difficulty progression is gentle", "Part distribution feels balanced"]'::jsonb,
    5
),
(
    'A1',
    'FAIRNESS_BIAS',
    'Fairness and Bias',
    'Evaluate whether test content is fair, inclusive, and free from unnecessary cultural bias.',
    '["Avoids culturally narrow assumptions", "No sensitive, offensive, or exclusionary wording", "Does not require specialist background knowledge", "Context remains accessible to typical learners"]'::jsonb,
    6
),
(
    'A1',
    'TECHNICAL_ACCURACY',
    'Technical Accuracy',
    'Evaluate technical consistency and presentation quality across the test.',
    '["Question numbering is consistent", "No missing options or broken references", "Formatting supports readability", "Spelling and grammar in prompts/options are clean"]'::jsonb,
    7
),
(
    'A1',
    'REVISION_ACTIONABILITY',
    'Revision Actionability',
    'Evaluate whether suggested improvements are concrete and implementable by teachers.',
    '["Feedback prioritizes major issues first", "Each issue includes a practical fix", "Recommendations are specific rather than generic", "Proposed changes are feasible for immediate revision"]'::jsonb,
    8
),
(
    'A2',
    'LEVEL_ALIGNMENT',
    'CEFR Level Alignment',
    'Evaluate whether the test language demand matches A2 elementary-level reading expectations.',
    '["Vocabulary is mostly high-frequency with limited low-frequency items", "Instructions are clear and straightforward", "Sentence complexity is controlled", "Inference demand remains basic"]'::jsonb,
    1
),
(
    'A2',
    'PASSAGE_QUALITY',
    'Passage Quality',
    'Evaluate readability, coherence, and suitability of passages for A2 learners.',
    '["Passages are short-to-medium length", "Ideas are logically sequenced", "Wording is concrete and understandable", "Topic selection is relevant and accessible"]'::jsonb,
    2
),
(
    'A2',
    'QUESTION_CLARITY',
    'Question Clarity and Validity',
    'Evaluate whether each question is unambiguous and aligned with intended reading outcomes.',
    '["Stems are concise and explicit", "No wording that causes multiple interpretations", "Items target clear evidence in text", "Question difficulty is appropriate for A2"]'::jsonb,
    3
),
(
    'A2',
    'DISTRACTOR_QUALITY',
    'Distractor Quality',
    'Evaluate quality and fairness of distractors in multiple-choice tasks.',
    '["Distractors are plausible but not misleadingly tricky", "No lexical/grammatical clues that reveal the key", "Option set is mutually exclusive", "One best answer can be justified with text evidence"]'::jsonb,
    4
),
(
    'A2',
    'SKILL_COVERAGE',
    'Skill Coverage and Balance',
    'Evaluate whether the test balances key A2 reading skills.',
    '["Covers gist, detail, and simple inference", "Items are distributed across passage sections", "No single skill dominates excessively", "Difficulty progression is reasonable"]'::jsonb,
    5
),
(
    'A2',
    'FAIRNESS_BIAS',
    'Fairness and Bias',
    'Evaluate inclusiveness and fairness for a diverse A2 learner population.',
    '["Avoids culturally exclusive references", "No sensitive or discriminatory content", "Tasks do not rely on privileged background knowledge", "Language remains accessible for non-native learners"]'::jsonb,
    6
),
(
    'A2',
    'TECHNICAL_ACCURACY',
    'Technical Accuracy',
    'Evaluate technical correctness and formatting consistency.',
    '["Numbering and labeling are consistent", "No missing text, options, or symbols", "Formatting supports scanning and comprehension", "No typos that alter meaning"]'::jsonb,
    7
),
(
    'A2',
    'REVISION_ACTIONABILITY',
    'Revision Actionability',
    'Evaluate whether revision recommendations are practical and prioritized.',
    '["Identifies highest-impact edits first", "Provides concrete rewrite directions", "Connects issues to expected learner impact", "Suggestions are feasible within normal teacher workflow"]'::jsonb,
    8
),
(
    'B1',
    'LEVEL_ALIGNMENT',
    'CEFR Level Alignment',
    'Evaluate whether the reading test aligns with B1 intermediate-level expectations.',
    '["Lexical range is appropriate for B1", "Sentence structures include moderate complexity", "Inference demand is present but controlled", "Task demands match B1 descriptors"]'::jsonb,
    1
),
(
    'B1',
    'PASSAGE_QUALITY',
    'Passage Quality',
    'Evaluate authenticity, coherence, and suitability of passages for B1 learners.',
    '["Passages have clear organization and paragraph logic", "Content supports meaningful comprehension tasks", "Wording avoids unnecessary ambiguity", "Length is suitable for time constraints"]'::jsonb,
    2
),
(
    'B1',
    'QUESTION_CLARITY',
    'Question Clarity and Validity',
    'Evaluate question precision and alignment with passage evidence.',
    '["Stems are precise and unambiguous", "Each item targets a distinct comprehension objective", "No trick wording or accidental ambiguity", "Correct key is supported by explicit or inferable evidence"]'::jsonb,
    3
),
(
    'B1',
    'DISTRACTOR_QUALITY',
    'Distractor Quality',
    'Evaluate quality of distractors and option set design.',
    '["Distractors are credible for B1 learners", "No option is trivially dismissible", "Option wording avoids overlap", "Exactly one defensible best answer exists"]'::jsonb,
    4
),
(
    'B1',
    'SKILL_COVERAGE',
    'Skill Coverage and Balance',
    'Evaluate balance across B1 reading subskills and cognitive demands.',
    '["Covers gist, detail, inference, and vocabulary in context", "Question distribution is balanced across parts", "Difficulty progression is coherent", "No over-concentration on a single micro-skill"]'::jsonb,
    5
),
(
    'B1',
    'FAIRNESS_BIAS',
    'Fairness and Bias',
    'Evaluate fairness and accessibility for a broad learner population.',
    '["Avoids bias-prone contexts", "No culturally narrow assumptions required to answer", "Sensitive topics are handled carefully", "Reading demand remains language-based rather than background-knowledge-based"]'::jsonb,
    6
),
(
    'B1',
    'TECHNICAL_ACCURACY',
    'Technical Accuracy',
    'Evaluate technical and editorial quality of the test.',
    '["Consistent numbering and references", "No duplicated or missing items", "Formatting is clean and readable", "Grammar/spelling in stems and options is correct"]'::jsonb,
    7
),
(
    'B1',
    'REVISION_ACTIONABILITY',
    'Revision Actionability',
    'Evaluate usefulness and practicality of proposed revisions.',
    '["Recommendations are prioritized by severity", "Each issue includes a concrete fix path", "Suggestions are specific and teacher-friendly", "Revision scope is realistic for iterative improvement"]'::jsonb,
    8
),
(
    'B2',
    'LEVEL_ALIGNMENT',
    'CEFR Level Alignment',
    'Evaluate whether the test aligns with B2 upper-intermediate reading expectations.',
    '["Lexical and syntactic complexity is suitable for B2", "Inference and interpretation demands are appropriate", "Task challenge is substantial but fair", "Items map to B2 reading outcomes"]'::jsonb,
    1
),
(
    'B2',
    'PASSAGE_QUALITY',
    'Passage Quality',
    'Evaluate passage authenticity, coherence, and cognitive accessibility at B2.',
    '["Passages are coherent and rhetorically structured", "Topic development supports deeper comprehension", "Language is challenging but not unnecessarily opaque", "Length and density are manageable within allotted time"]'::jsonb,
    2
),
(
    'B2',
    'QUESTION_CLARITY',
    'Question Clarity and Validity',
    'Evaluate whether questions validly target intended comprehension constructs.',
    '["Question intent is explicit and measurable", "No ambiguous or multi-key stems", "Items target higher-order comprehension where appropriate", "Answer key remains evidence-grounded"]'::jsonb,
    3
),
(
    'B2',
    'DISTRACTOR_QUALITY',
    'Distractor Quality',
    'Evaluate sophistication and fairness of distractor design.',
    '["Distractors are nuanced and plausible", "No clues from option form or length", "Options are distinct with minimal overlap", "Only one option is best supported by text"]'::jsonb,
    4
),
(
    'B2',
    'SKILL_COVERAGE',
    'Skill Coverage and Balance',
    'Evaluate breadth and balance of B2 reading skill coverage.',
    '["Balanced coverage of gist, detail, inference, tone, and vocabulary in context", "Question load is distributed fairly across passage parts", "Difficulty progression is deliberate", "No cluster of redundant item types"]'::jsonb,
    5
),
(
    'B2',
    'FAIRNESS_BIAS',
    'Fairness and Bias',
    'Evaluate whether test content remains fair and inclusive at higher difficulty.',
    '["No unfair dependence on specific cultural capital", "Sensitive topics are contextualized responsibly", "Language challenge is not confused with bias", "All learners have equitable chance to demonstrate reading ability"]'::jsonb,
    6
),
(
    'B2',
    'TECHNICAL_ACCURACY',
    'Technical Accuracy',
    'Evaluate precision, consistency, and editorial polish.',
    '["All numbering, labels, and references are consistent", "No missing/duplicated questions or options", "Layout supports efficient test navigation", "No language errors that affect validity"]'::jsonb,
    7
),
(
    'B2',
    'REVISION_ACTIONABILITY',
    'Revision Actionability',
    'Evaluate whether suggested revisions are specific, prioritized, and actionable.',
    '["Critical issues are ranked clearly", "Each issue includes concrete remediation steps", "Suggestions target validity, fairness, and clarity", "Recommendations are realistic for teacher implementation"]'::jsonb,
    8
)
ON CONFLICT (level, code) DO NOTHING;
