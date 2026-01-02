from django.db import models
from django.core.validators import MinValueValidator


# Create your models here.
class Test(models.Model):
    title = models.CharField(max_length=255)
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
    completed_bonus = models.IntegerField(validators=[MinValueValidator(0)], default=0)
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


class ReceptiveTest(models.Model):
    test = models.OneToOneField(Test, on_delete=models.CASCADE, primary_key=True)

    total_score = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    base_qualified_bonus = models.IntegerField(
        validators=[MinValueValidator(0)], default=0
    )

    def __str__(self):
        return f"Receptive Test for {self.test.title}"

    class Meta:
        db_table = "receptive_test"


class ProductiveTest(models.Model):
    test = models.OneToOneField(Test, on_delete=models.CASCADE, primary_key=True)

    format = models.CharField(max_length=1, choices=[])  # Update choices when needed
    question_text = models.TextField()
    resources = models.JSONField(default=dict)
    criteria = models.JSONField(default=dict)

    def __str__(self):
        return f"Productive Test for {self.test.title}"

    class Meta:
        db_table = "productive_test"


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

    option_label = models.CharField(max_length=1)
    answer_text = models.TextField(blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    resources = models.JSONField(default=dict)

    def __str__(self):
        return f"Answer {self.option_label} for Question {self.receptive_question.question_number} in Part {self.receptive_question.receptive_part.order} of {self.receptive_question.receptive_part.receptive_test.test.title}"

    class Meta:
        db_table = "receptive_answer"
