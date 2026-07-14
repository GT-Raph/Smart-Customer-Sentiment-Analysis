import hashlib
import hmac

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.utils import timezone


class Bank(models.Model):
    name = models.CharField(
        max_length=150,
    )

    code = models.SlugField(
        max_length=30,
        unique=True,
        help_text=(
            "Unique bank code, for example "
            "FIDELITY_GH or BANK_A"
        ),
    )

    api_key_hash = models.CharField(
        max_length=64,
        blank=True,
        editable=False,
    )

    api_key_rotated_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "tenant_bank"
        ordering = ("name",)

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()

        super().save(
            *args,
            **kwargs,
        )

    def set_api_key(self, raw_key: str) -> None:
        if not raw_key or len(raw_key) < 24:
            raise ValueError(
                "The API key must contain at least "
                "24 characters."
            )

        self.api_key_hash = hashlib.sha256(
            raw_key.encode("utf-8")
        ).hexdigest()

        self.api_key_rotated_at = timezone.now()

    def check_api_key(self, raw_key: str) -> bool:
        if not self.api_key_hash or not raw_key:
            return False

        supplied_hash = hashlib.sha256(
            raw_key.encode("utf-8")
        ).hexdigest()

        return hmac.compare_digest(
            self.api_key_hash,
            supplied_hash,
        )

    @property
    def has_api_key(self):
        return bool(self.api_key_hash)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Branch(models.Model):
    bank = models.ForeignKey(
        Bank,
        on_delete=models.PROTECT,
        related_name="branches",
    )

    name = models.CharField(
        max_length=100,
    )

    code = models.SlugField(
        max_length=30,
        help_text=(
            "Branch code, for example "
            "RIDGE_TOWERS"
        ),
    )

    pc_prefix = models.CharField(
        max_length=80,
        help_text=(
            "Expected computer-name prefix "
            "for this branch"
        ),
    )

    location = models.CharField(
        max_length=200,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "tenant_branch"
        ordering = (
            "bank__name",
            "name",
        )

        constraints = [
            models.UniqueConstraint(
                fields=(
                    "bank",
                    "code",
                ),
                name=(
                    "uniq_branch_code_per_bank"
                ),
            ),

            models.UniqueConstraint(
                fields=(
                    "bank",
                    "pc_prefix",
                ),
                name=(
                    "uniq_pc_prefix_per_bank"
                ),
            ),
        ]

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        self.pc_prefix = self.pc_prefix.strip().upper()

        super().save(
            *args,
            **kwargs,
        )

    def __str__(self):
        return (
            f"{self.bank.code} - "
            f"{self.name}"
        )


class CustomUser(AbstractUser):
    bank = models.ForeignKey(
        Bank,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )

    def clean(self):
        super().clean()

        if (
            self.branch_id
            and self.bank_id
            and self.branch.bank_id
            != self.bank_id
        ):
            raise ValidationError(
                {
                    "branch": (
                        "The selected branch does not "
                        "belong to this bank."
                    )
                }
            )

        if (
            not self.is_superuser
            and not self.bank_id
            and not self.branch_id
        ):
            raise ValidationError(
                {
                    "bank": (
                        "A non-superuser must belong "
                        "to a bank."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if self.branch_id:
            self.bank_id = (
                self.branch.bank_id
            )

        super().save(
            *args,
            **kwargs,
        )

    @property
    def is_bank_admin(self):
        return self.is_superuser or (
            self.bank_id is not None
            and self.branch_id is None
        )


class UserPreference(models.Model):
    DATE_RANGE_DAY = "day"
    DATE_RANGE_WEEK = "week"
    DATE_RANGE_14_DAYS = "14days"
    DATE_RANGE_MONTH = "month"

    DATE_RANGE_CHOICES = (
        (
            DATE_RANGE_DAY,
            "Today",
        ),
        (
            DATE_RANGE_WEEK,
            "Last 7 days",
        ),
        (
            DATE_RANGE_14_DAYS,
            "Last 14 days",
        ),
        (
            DATE_RANGE_MONTH,
            "Last 30 days",
        ),
    )

    HOURLY_TODAY = "today"
    HOURLY_YESTERDAY = "yesterday"

    HOURLY_RANGE_CHOICES = (
        (
            HOURLY_TODAY,
            "Today",
        ),
        (
            HOURLY_YESTERDAY,
            "Yesterday",
        ),
    )

    AUTO_REFRESH_CHOICES = (
        (
            0,
            "Disabled",
        ),
        (
            30,
            "Every 30 seconds",
        ),
        (
            60,
            "Every minute",
        ),
        (
            120,
            "Every 2 minutes",
        ),
        (
            300,
            "Every 5 minutes",
        ),
    )

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="preferences",
    )

    default_date_range = models.CharField(
        max_length=10,
        choices=DATE_RANGE_CHOICES,
        default=DATE_RANGE_14_DAYS,
    )

    default_hourly_range = models.CharField(
        max_length=12,
        choices=HOURLY_RANGE_CHOICES,
        default=HOURLY_TODAY,
    )

    default_branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        related_name="default_for_users",
        null=True,
        blank=True,
    )

    auto_refresh_seconds = models.PositiveIntegerField(
        choices=AUTO_REFRESH_CHOICES,
        default=0,
    )

    compact_mode = models.BooleanField(
        default=False,
    )

    reduce_motion = models.BooleanField(
        default=False,
    )

    email_weekly_summary = models.BooleanField(
        default=False,
    )

    notify_negative = models.BooleanField(
        default=False,
    )

    negative_threshold = models.PositiveSmallIntegerField(
        default=35,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(100),
        ],
        help_text=(
            "Alert when negative emotions meet "
            "or exceed this percentage."
        ),
    )

    minimum_detections = models.PositiveIntegerField(
        default=20,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(100000),
        ],
        help_text=(
            "Minimum number of detections before "
            "an alert may be triggered."
        ),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "monitor_user_preference"

    def clean(self):
        super().clean()

        if not self.default_branch_id:
            return

        user = self.user

        if user.is_superuser:
            return

        if (
            user.branch_id
            and self.default_branch_id
            != user.branch_id
        ):
            raise ValidationError(
                {
                    "default_branch": (
                        "A branch user can only select "
                        "their assigned branch."
                    )
                }
            )

        if (
            user.bank_id
            and self.default_branch.bank_id
            != user.bank_id
        ):
            raise ValidationError(
                {
                    "default_branch": (
                        "The selected branch does not "
                        "belong to your bank."
                    )
                }
            )

    def __str__(self):
        return (
            f"Preferences for "
            f"{self.user.username}"
        )


class BankSettings(models.Model):
    bank = models.OneToOneField(
        Bank,
        on_delete=models.CASCADE,
        related_name="configuration",
    )

    timezone = models.CharField(
        max_length=64,
        default="Africa/Accra",
    )

    image_retention_days = models.PositiveIntegerField(
        default=30,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(3650),
        ],
    )

    record_retention_days = models.PositiveIntegerField(
        default=365,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(3650),
        ],
    )

    delete_images_after_retention = (
        models.BooleanField(
            default=True,
        )
    )

    offline_after_minutes = models.PositiveIntegerField(
        default=15,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(1440),
        ],
        help_text=(
            "A computer is marked offline when no "
            "capture is received within this period."
        ),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "tenant_bank_settings"
        verbose_name_plural = "Bank settings"

    def __str__(self):
        return (
            f"Settings for {self.bank.name}"
        )


class Visitor(models.Model):
    bank = models.ForeignKey(
        Bank,
        on_delete=models.CASCADE,
        related_name="visitors",
    )

    face_id = models.CharField(
        max_length=128,
    )

    first_seen = models.DateTimeField(
        default=timezone.now,
    )

    last_seen = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        db_table = "analytics_visitor"

        constraints = [
            models.UniqueConstraint(
                fields=(
                    "bank",
                    "face_id",
                ),
                name="uniq_face_per_bank",
            )
        ]

        indexes = [
            models.Index(
                fields=(
                    "bank",
                    "last_seen",
                ),
            )
        ]

    def __str__(self):
        return (
            f"{self.bank.code}:"
            f"{self.face_id}"
        )


class CapturedSnapshot(models.Model):
    STATUS_PENDING = "pending"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = (
        (
            STATUS_PENDING,
            "Pending",
        ),
        (
            STATUS_DONE,
            "Done",
        ),
        (
            STATUS_FAILED,
            "Failed",
        ),
    )

    job_id = models.CharField(
        max_length=50,
        unique=True,
    )

    bank = models.ForeignKey(
        Bank,
        on_delete=models.PROTECT,
        related_name="snapshots",
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="snapshots",
    )

    visitor = models.ForeignKey(
        Visitor,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )

    pc_name = models.CharField(
        max_length=128,
    )

    image_path = models.CharField(
        max_length=500,
    )

    timestamp = models.DateTimeField(
        default=timezone.now,
    )

    emotion = models.CharField(
        max_length=32,
        blank=True,
    )

    confidence = models.FloatField(
        null=True,
        blank=True,
    )

    emotion_vector = models.JSONField(
        null=True,
        blank=True,
    )

    embedding = models.JSONField(
        null=True,
        blank=True,
    )

    processed = models.BooleanField(
        default=True,
    )

    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=STATUS_DONE,
    )

    processing_error = models.TextField(
        blank=True,
    )

    class Meta:
        db_table = "analytics_snapshot"
        ordering = ("-timestamp",)

        indexes = [
            models.Index(
                fields=(
                    "bank",
                    "timestamp",
                ),
            ),

            models.Index(
                fields=(
                    "branch",
                    "timestamp",
                ),
            ),

            models.Index(
                fields=(
                    "bank",
                    "visitor",
                    "timestamp",
                ),
            ),
        ]

    def clean(self):
        if (
            self.branch_id
            and self.bank_id
            and self.branch.bank_id
            != self.bank_id
        ):
            raise ValidationError(
                "Snapshot branch and bank "
                "do not match."
            )

        if (
            self.visitor_id
            and self.bank_id
            and self.visitor.bank_id
            != self.bank_id
        ):
            raise ValidationError(
                "Snapshot visitor and bank "
                "do not match."
            )

    def __str__(self):
        return (
            f"{self.bank.code}/"
            f"{self.branch.code} - "
            f"{self.visitor.face_id}"
        )