from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.
class UserLevel(models.Model):
    level_number = models.IntegerField(unique=True, validators=[MinValueValidator(1)])
    level_title = models.CharField(max_length=50)
    level_icon = models.URLField(max_length=200, null=True, blank=True)
    min_xp = models.IntegerField(validators=[MinValueValidator(0)])
    max_xp = models.IntegerField(validators=[MinValueValidator(0)])

    def clean(self):
        if self.min_xp >= self.max_xp:
            raise ValidationError("min_xp must be less than max_xp")
        
    def __str__(self):
        return f"Level {self.level_number} - {self.level_title}: {self.min_xp} - {self.max_xp} XP"
    
    class Meta:
        db_table = "user_level"
        ordering = ["min_xp"]


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


class EXPBonusRule(models.Model):
    min_percentage = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Minimum required percentage",
    )
    max_percentage = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Maximum percentage achievable",
    )
    exp_percentage = models.FloatField(
        validators=[MinValueValidator(0.0)],
        help_text="EXP percentage awarded",
    )
    rating = models.TextField()
    feedback_message = models.TextField()

    def clean(self):
        super().clean()

        if self.min_percentage is not None and self.max_percentage is not None:
            if self.min_percentage >= self.max_percentage:
                raise ValidationError(
                    {
                        "min_percentage": "Min percentage must be less than max percentage."
                    }
                )

            overlapping = EXPBonusRule.objects.filter(
                min_percentage__lt=self.max_percentage,
                max_percentage__gt=self.min_percentage,
            )

            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)

            if overlapping.exists():
                raise ValidationError(
                    "This percentage range overlaps with an existing EXP Bonus Rule."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"EXP Bonus Rule: {self.min_percentage}% - {self.max_percentage}% => {self.exp_percentage}% EXP"

    class Meta:
        db_table = "exp_bonus_rule"
        constraints = [
            models.UniqueConstraint(
                fields=["min_percentage", "max_percentage"],
                name="unique_exp_bonus_rule_range",
            )
        ]


class StreakRewardRule(models.Model):
    streak_day = models.IntegerField(
        unique=True,
        validators=[MinValueValidator(1)],
        help_text="Required streak day to unlock this reward",
    )
    xp_reward = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="XP awarded when user reaches streak_day",
    )
    ai_turn_reward = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total AI turns shown in reward config",
    )

    def __str__(self):
        return (
            f"Streak {self.streak_day}d: +{self.xp_reward} XP, "
            f"+{self.ai_turn_reward} AI turns "
        )

    class Meta:
        db_table = "streak_reward_rule"
        ordering = ["streak_day"]


