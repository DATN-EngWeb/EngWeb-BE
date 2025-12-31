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
            ("C1", "C1"),
            ("C2", "C2"),
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

    format = models.CharField(max_length=1, choices=[]) # Update choices when needed
    question_text = models.TextField()
    resources = models.JSONField(default=dict)
    criterias = models.JSONField(default=dict)

    def __str__(self):
        return f"Productive Test for {self.test.title}"
    
    class Meta:
        db_table = 'productive_test'
