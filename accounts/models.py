from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator
from django.db import models

import uuid

# custom user manager
class CustomUserManager(BaseUserManager):
    def create_user(
        self, 
        username, 
        email, 
        password=None, 
        **extra_fields
    ):
        if not username:
            raise ValueError("Username is required")
        
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)

        if password:
            user.set_password(password)  # create user through registration form
        else:
            user.set_unusable_password()  # create user through social authentication
        user.save(using=self._db)

        return user

    def create_superuser(
        self, 
        username, 
        email, 
        password=None, 
        **extra_fields
    ):
        extra_fields.setdefault("role", "A")
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("avatar", "users/avatars/admin-avatar.png")
        user = self.create_user(
            username, 
            email, 
            password, 
            **extra_fields
        )

        return user

# custom user model
class User(AbstractUser):
    # BaseAbstractUser/AbstractUser default fields : (password, last_login)/(username, date_joined, is_active)
    email = models.EmailField(unique=True)  # override email to make it unique
    file_storage_uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False) # renamed folder name for file storage
    full_name = models.CharField(max_length=100, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    avatar = models.ImageField(
        upload_to="users/avatars/",
        null=True,
        blank=True,
        default="users/avatars/default-avatar.jpg",
    )
    cover = models.ImageField(
        upload_to="users/covers/",
        null=True,
        blank=True,
        default="users/covers/default-cover.jpg",
    )
    status = models.CharField(
        max_length=1,
        choices=[
            ("P", "Pending Verification"), # not verified OTP yet (both)
            ("I", "Incomplete Profile"),  # verified OTP, incomplete profile (only teacher)
            ("W", "Waiting Approval"),  # complete profile, waiting for approval (only teacher)
            ("V", "Verified"),  # verified OTP/profile for student/teacher
            ("D", "Disabled"),  # disabled (both)
        ],
        default="P",
    )
    role = models.CharField(
        max_length=1,
        choices=[
            ("S", "Student"),
            ("T", "Teacher"),
            ("A", "Admin"),
        ],
        default="S",
    )
    updated_at = models.DateTimeField(auto_now=True)

    # remove default fields are not used
    first_name = None
    last_name = None

    # override user manager
    objects = CustomUserManager()

    # properties for admin panel compatibility
    @property
    def is_staff(self):
        return self.role == "A"

    @property
    def is_superuser(self):
        return self.role == "A"

    def __str__(self):
        if self.full_name:
            return self.full_name
        else:
            return self.email

    class Meta:
        db_table = "user"
        indexes = [
            models.Index(fields=["username"]),
        ]

# teacher model
class Teacher(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        primary_key=True, 
        related_name="teacher"
    )
    current_workplace = models.CharField(max_length=255)
    teacher_type = models.CharField(
        max_length=1,
        choices=[
            ("S", "School Teacher"),  # regular teacher (at school)
            ("C", "Center Teacher"),  # center teacher
            ("F", "Freelance Teacher"),  # freelance teacher
        ],
        default="F",
    )
    experience_year = models.IntegerField(validators=[MinValueValidator(0)])
    introduction = models.TextField()
    credentials = models.JSONField(default=dict)

    # AI interaction turns for teacher
    weekly_ai_turn = models.IntegerField(validators=[MinValueValidator(0)], default=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user.full_name:
            return self.user.full_name
        return self.user.username

    class Meta:
        db_table = "teacher"

# student model
class Student(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        primary_key=True, 
        related_name="student"
    )

    # points and rewards
    cumulative_point = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    weekly_point = models.IntegerField(validators=[MinValueValidator(0)], default=0)

    # ai interaction turns
    weekly_ai_turn = models.IntegerField(validators=[MinValueValidator(0)], default=4)
    bonus_ai_turn = models.IntegerField(validators=[MinValueValidator(0)], default=0)

    # test tracking
    completed_test = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    qualified_test = models.IntegerField(validators=[MinValueValidator(0)], default=0)

    # streak tracking
    last_submitted_date = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
    )
    streak_count = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    max_streak = models.IntegerField(validators=[MinValueValidator(0)], default=0)

    # level progression
    level = models.ForeignKey(
        "user_progress.UserLevel",
        on_delete=models.PROTECT,
        related_name="students",
        default=1,
    )

    # timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user.full_name:
            return self.user.full_name
        else:
            return self.user.email

    class Meta:
        db_table = "student"
