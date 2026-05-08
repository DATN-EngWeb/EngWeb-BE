from django.db import models


class TestFeedback(models.Model):
    test = models.ForeignKey("tests.Test", on_delete=models.CASCADE)
    teacher = models.ForeignKey(
        "accounts.Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(
        max_length=10,
        choices=[
            ("A", "AI"),
            ("T", "Teacher"),
        ],
        default="T",
    )
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Feedback for test {self.test_id}"

    class Meta:
        db_table = "test_feedback"
