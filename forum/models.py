from accounts.models import User
from test_histories.models import ProductiveTestHistory

from django.db import models

class Post(models.Model):
    productive_test_history = models.ForeignKey(
        ProductiveTestHistory, 
        on_delete=models.CASCADE,
        related_name='posts'
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    like_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "post"

class PostComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Comment by {self.user_id} on post {self.post_id}"

    class Meta:
        db_table = "post_comment"

class PostReaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=1,
        choices=[
            ("L", "Like"),
            ("U", "Unlike"),
        ],
        default="L",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reaction {self.status} by {self.user_id} on post {self.post_id}"

    class Meta:
        db_table = "post_reaction"
        unique_together = ("user", "post")
