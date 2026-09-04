from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class Organization(models.Model):
    class Plan(models.TextChoices):
        FREE = "free", "Free"
        STARTER = "starter", "Starter"
        BUSINESS = "business", "Business"
        ENTERPRISE = "enterprise", "Enterprise"

    class SubscriptionStatus(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        SUSPENDED = "suspended", "Suspended"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=80, unique=True)
    plan = models.CharField(max_length=20, choices=Plan.choices, default=Plan.FREE)
    subscription_status = models.CharField(
        max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.TRIALING
    )
    monthly_analysis_limit = models.PositiveIntegerField(
        default=1000, help_text="Use 0 for unlimited analyses"
    )
    billing_customer_reference = models.CharField(max_length=128, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class MonthlyUsage(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="monthly_usage"
    )
    period_start = models.DateField()
    analyses_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "period_start"],
                name="unique_monthly_usage_period",
            )
        ]
        ordering = ["-period_start"]

    def __str__(self) -> str:
        return f"{self.organization.slug} — {self.period_start}: {self.analyses_count}"


class Branch(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="branches"
    )
    name = models.CharField(max_length=100)
    pc_prefix = models.CharField(
        max_length=50,
        unique=True,
        help_text="Globally unique PC name prefix for this branch",
    )
    location = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["organization__name", "name"]

    def __str__(self) -> str:
        return f"{self.organization.name} — {self.name} ({self.pc_prefix})"

    @property
    def code_prefix(self) -> str:
        return self.pc_prefix


class CustomUser(AbstractUser):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Assigned Branch",
    )

    def clean(self) -> None:
        super().clean()
        if self.branch_id and self.organization_id:
            if self.branch.organization_id != self.organization_id:
                from django.core.exceptions import ValidationError

                raise ValidationError("The selected branch belongs to another organization.")


class UserProfile(models.Model):
    """Retained for backwards compatibility; new code uses fields on CustomUser."""

    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="profile"
    )
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def is_superadmin(self) -> bool:
        return self.user.is_superuser

    @property
    def pc_prefix(self) -> str | None:
        return self.branch.pc_prefix if self.branch else None

    def __str__(self) -> str:
        return f"{self.user.username} — {self.branch or 'No branch'}"


class Device(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="devices"
    )
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="devices")
    name = models.CharField(max_length=100)
    pc_name = models.CharField(max_length=128)
    api_key_prefix = models.CharField(max_length=24, unique=True)
    api_key_hash = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "pc_name"], name="unique_device_pc_per_org"
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.branch_id and self.organization_id:
            if self.branch.organization_id != self.organization_id:
                from django.core.exceptions import ValidationError

                raise ValidationError("The device branch belongs to another organization.")

    def __str__(self) -> str:
        return f"{self.organization.name} — {self.name}"


class Visitor(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="visitors"
    )
    face_id = models.CharField(max_length=128)
    first_seen = models.DateTimeField()
    last_seen = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "face_id"], name="unique_face_per_org"
            )
        ]
        indexes = [models.Index(fields=["organization", "face_id"])]

    def __str__(self) -> str:
        return f"Visitor {self.face_id}"


class CapturedSnapshot(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    job_id = models.CharField(max_length=26, unique=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="snapshots"
    )
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="snapshots")
    device = models.ForeignKey(Device, on_delete=models.PROTECT, related_name="snapshots")
    visitor = models.ForeignKey(
        Visitor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="snapshots",
    )
    pc_name = models.CharField(max_length=128)
    session_id = models.CharField(max_length=64, blank=True, db_index=True)
    image_path = models.TextField(null=True, blank=True)
    upload_content_type = models.CharField(max_length=64, blank=True)
    upload_size_bytes = models.PositiveIntegerField(default=0)
    timestamp = models.DateTimeField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.QUEUED
    )
    emotion = models.CharField(max_length=32, null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    emotion_vector = models.JSONField(null=True, blank=True)
    processed = models.BooleanField(default=False)
    embedding = models.JSONField(null=True, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "captured_snapshots"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["organization", "branch", "timestamp"]),
            models.Index(fields=["status", "timestamp"]),
            models.Index(fields=["visitor", "timestamp"]),
        ]

    def __str__(self) -> str:
        visitor = self.visitor.face_id if self.visitor else "unassigned"
        return f"{self.job_id} — {visitor} — {self.status}"
