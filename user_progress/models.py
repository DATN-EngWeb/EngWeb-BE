from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

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
