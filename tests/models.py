from django.db import models
from django.core.validators import MinValueValidator


# Create your models here.
class Test(models.Model):
    title = models.CharField(max_length=255)
    type = models.CharField(
        choices=[
            ("R", "Receptive test"),
            ("P", "Productive test"),
        ],
        max_length=1,
        default="R",
    )

    level = models.CharField(
        max_length=2,
        choices=[
            ("B1", "B1"),
            ("B2", "B2"),
            ("A1", "A1"),
            ("A2", "A2"),
        ],
        default="A1",
    )
    skill = models.CharField(
        max_length=1,
        choices=[
            ("R", "Reading"),
            ("L", "Listening"),
            ("S", "Speaking"),
            ("W", "Writing"),
        ],
        default="R",
    )
    time = models.IntegerField(
        help_text="Time in minutes", validators=[MinValueValidator(1)]
    )
    description = models.TextField()
    status = models.CharField(
        max_length=1,
        choices=[
            ("D", "Draft"),
            ("I", "In Review"),
            ("P", "Published"),
            ("R", "Removed"),
        ],
        default="D",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        "accounts.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        related_name="tests_created",
    )

    def __str__(self):
        # (Skill - Level) Title (first 30 chars only)
        return f"({self.skill} - {self.level}) {self.title[:30]}"

    class Meta:
        db_table = "test"
        constraints = [
            models.CheckConstraint(
                condition=(
                    # type=R (Receptive) → skill must be R (Reading) or L (Listening)
                    models.Q(type="R", skill__in=["R", "L"])
                    |
                    # type=P (Productive) → skill must be S (Speaking) or W (Writing)
                    models.Q(type="P", skill__in=["S", "W"])
                ),
                name="test_type_skill_compatibility",
            ),
        ]


class ReceptiveTest(models.Model):
    test = models.OneToOneField(
        Test, on_delete=models.CASCADE, primary_key=True, related_name="receptive_test"
    )

    total_score = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    base_qualified_bonus = models.IntegerField(
        validators=[MinValueValidator(0)], default=0
    )

    def __str__(self):
        return f"Receptive Test for {self.test.title}"

    class Meta:
        db_table = "receptive_test"


class ReceptivePart(models.Model):
    receptive_test = models.ForeignKey(
        ReceptiveTest, on_delete=models.CASCADE, related_name="receptive_parts"
    )

    order = models.IntegerField(validators=[MinValueValidator(1)])
    format = models.CharField(
        max_length=1,
        choices=[
            ("A", "Listening - Multiple Choice images"),
            ("B", "Listening - Multiple Choice text (one audio per question)"),
            ("C", "Listening - Multiple Choice text (one audio for all questions)"),
            ("D", "Listening - Fill in the blanks"),
            ("E", "Listening - Matching"),
            ("F", "Reading - Multiple Choice (short text)"),
            ("G", "Reading - Multiple Choice (long text)"),
            ("H", "Reading - Fill in the blanks (multiple choice)"),
            ("I", "Reading - Fill in the blanks (text)"),
            ("J", "Reading - Matching"),
        ],
    )
    description = models.TextField()
    content = models.TextField(blank=True, null=True)
    score = models.IntegerField(
        validators=[MinValueValidator(0)], default=0
    )  # Score is calculated depending on the questions in the part
    resources = models.JSONField(default=dict)

    def __str__(self):
        return f"Part {self.order} of {self.receptive_test.test.title}"

    class Meta:
        db_table = "receptive_part"


class ReceptiveQuestion(models.Model):
    receptive_part = models.ForeignKey(
        ReceptivePart, on_delete=models.CASCADE, related_name="receptive_questions"
    )

    question_number = models.IntegerField(validators=[MinValueValidator(1)])
    content = models.TextField()
    explanation = models.TextField(blank=True, null=True)
    score = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    resources = models.JSONField(default=dict)

    def __str__(self):
        return f"Question {self.question_number} of Part {self.receptive_part.order} in {self.receptive_part.receptive_test.test.title}"

    class Meta:
        db_table = "receptive_question"


class ReceptiveAnswer(models.Model):
    receptive_question = models.ForeignKey(
        ReceptiveQuestion, on_delete=models.CASCADE, related_name="receptive_answers"
    )

    option_label = models.CharField(max_length=1, blank=True, null=True)
    answer_text = models.TextField(blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    resources = models.JSONField(default=dict)

    def __str__(self):
        return f"Answer {self.option_label} for Question {self.receptive_question.question_number} in Part {self.receptive_question.receptive_part.order} of {self.receptive_question.receptive_part.receptive_test.test.title}"

    class Meta:
        db_table = "receptive_answer"


class ProductiveTest(models.Model):
    test = models.OneToOneField(
        Test, on_delete=models.CASCADE, primary_key=True, related_name="productive_test"
    )

    format = models.CharField(
        max_length=1,
        choices=[
            ("A", "Writing - Email"),
            ("B", "Writing - Article"),
            ("C", "Writing - Tell a story based on pictures"),
            ("D", "Writing - Essay"),
            ("E", "Writing - Letter"),
            ("F", "Writing - Reviews"),
            ("G", "Speaking - Narrative"),
            ("H", "Speaking - Description"),
            ("I", "Speaking - Social argument"),
            ("J", "Speaking - Reading aloud"),
        ],
    )
    topic = models.TextField(blank=True, default="")
    description = models.TextField(
        blank=True, default=""
    )  # save url link to the description content
    min_word = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    glue_text = models.TextField(blank=True, null=True)
    glue_resources = models.JSONField(default=dict)

    def __str__(self):
        return f"Productive Test for {self.test.title}"

    class Meta:
        db_table = "productive_test"


class WritingCriteriaTemplate(models.Model):
    level = models.CharField(
        max_length=2,
        choices=[
            ("B1", "B1"),
            ("B2", "B2"),
            ("A1", "A1"),
            ("A2", "A2"),
        ],
    )
    band = models.IntegerField(validators=[MinValueValidator(1)])
    content = models.TextField(null=True, blank=True)
    communicative_achievement = models.TextField(null=True, blank=True)
    organisation = models.TextField(null=True, blank=True)
    language = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Level: {self.level}, Band: {self.band}"

    class Meta:
        db_table = "writing_criteria_template"
        constraints = [
            models.UniqueConstraint(fields=["level", "band"], name="unique_level_band")
        ]


class CompletedBonus(models.Model):
    skill = models.CharField(
        max_length=1,
        choices=[
            ("R", "Reading"),
            ("L", "Listening"),
            ("S", "Speaking"),
            ("W", "Writing"),
        ],
    )
    level = models.CharField(
        max_length=2,
        choices=[
            ("B1", "B1"),
            ("B2", "B2"),
            ("A1", "A1"),
            ("A2", "A2"),
        ],
    )
    completed_bonus = models.IntegerField(validators=[MinValueValidator(0)], default=0)

    def __str__(self):
        return (
            f"Skill: {self.skill}, Level: {self.level}, Bonus: {self.completed_bonus}"
        )

    class Meta:
        db_table = "completed_bonus"
        constraints = [
            models.UniqueConstraint(
                fields=["skill", "level"], name="unique_skill_level"
            )
        ]
