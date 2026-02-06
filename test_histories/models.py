from django.db import models


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
    ai_feedback = models.TextField(null=True, blank=True)
    earned_bonus_point = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        # Auto-calculate total_time
        if self.start_time and self.end_time:
            time_diff = self.end_time - self.start_time
            self.total_time = int(time_diff.total_seconds())

        super().save(*args, **kwargs)

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
