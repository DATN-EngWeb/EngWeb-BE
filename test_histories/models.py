from django.db import models
from django.core.validators import MinValueValidator


# Create your models here.
class ProductiveTestHistory(models.Model):
    student = models.ForeignKey(
        "accounts.Student",
        on_delete=models.CASCADE,
        related_name="productive_test_histories",
    )
    productive_test = models.ForeignKey(
        "tests.ProductiveTest", on_delete=models.CASCADE, related_name="histories"
    )
    attempt = models.IntegerField(default=1)

    type = models.CharField(
        max_length=1,
        choices=[
            ("D", "Draft"),
            ("S", "Submission"),
        ],
        default="D",
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    total_time = models.IntegerField(null=True, blank=True)  # in seconds

    audio_path = models.TextField(null=True, blank=True)
    user_answer_text = models.TextField(null=True, blank=True)
    user_note_text = models.TextField(null=True, blank=True)
    ai_feedback = models.JSONField(null=True, blank=True)
    earned_bonus_point = models.IntegerField(default=0)

    def __str__(self):
        type_label = "Draft" if self.type == "D" else f"Attempt {self.attempt}"
        return f"{self.student.user.username} - {self.productive_test.test.title} ({type_label})"

    class Meta:
        db_table = "productive_test_history"
        unique_together = ("student", "productive_test", "attempt")
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["student", "productive_test", "attempt", "type"]),
        ]


class ReceptiveTestHistory(models.Model):
    student = models.ForeignKey(
        "accounts.Student",
        on_delete=models.CASCADE,
        related_name="receptive_test_histories",
    )
    receptive_test = models.ForeignKey(
        "tests.ReceptiveTest", on_delete=models.CASCADE, related_name="histories"
    )

    attempt = models.IntegerField(default=1)

    type = models.CharField(
        max_length=1,
        choices=[
            ("D", "Draft"),
            ("S", "Submission"),
        ],
        default="D",
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    total_time = models.IntegerField(null=True, blank=True)  # in seconds

    total_score = models.IntegerField(
        validators=[MinValueValidator(0)], default=0, null=True, blank=True
    )
    bonus_point = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    earned_bonus_point = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        db_table = "receptive_test_history"
        unique_together = ("student", "receptive_test", "attempt")
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["student", "receptive_test", "attempt", "type"]),
        ]


class ReceptiveAnswerHistory(models.Model):
    receptive_test_history = models.ForeignKey(
        ReceptiveTestHistory, on_delete=models.CASCADE, related_name="answer_histories"
    )
    receptive_question = models.ForeignKey(
        "tests.ReceptiveQuestion",
        on_delete=models.CASCADE,
        related_name="answer_histories",
    )
    receptive_answer = models.ForeignKey(
        "tests.ReceptiveAnswer",
        on_delete=models.CASCADE,
        related_name="answer_histories",
        null=True,
        blank=True,
    )

    user_answer_text = models.TextField(null=True, blank=True)
    is_correct = models.BooleanField(default=False, null=True, blank=True)

    class Meta:
        db_table = "receptive_answer_history"
        unique_together = (
            "receptive_test_history",
            "receptive_question",
        )
        indexes = [
            models.Index(
                fields=[
                    "receptive_test_history",
                    "receptive_question",
                    "receptive_answer",
                ]
            ),
        ]
