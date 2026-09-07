from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models


class Branch(models.Model):
    """A physical location within this self-hosted installation."""

    name = models.CharField(max_length=100)
    pc_prefix = models.CharField(
        max_length=50,
        unique=True,
        help_text="Globally unique PC name prefix for this branch",
    )
    location = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.pc_prefix})"

    @property
    def code_prefix(self) -> str:
        return self.pc_prefix


class CustomUser(AbstractUser):
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Assigned Branch",
    )


class UserProfile(models.Model):
    """Retained for backwards compatibility; use CustomUser.branch in new code."""

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
        return f"{self.user.username} - {self.branch or 'No branch'}"


class Device(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="devices")
    name = models.CharField(max_length=100)
    pc_name = models.CharField(max_length=128, unique=True)
    api_key_prefix = models.CharField(max_length=24, unique=True)
    api_key_hash = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.pc_name})"


class Visitor(models.Model):
    face_id = models.CharField(max_length=128, unique=True)
    first_seen = models.DateTimeField()
    last_seen = models.DateTimeField()

    def __str__(self) -> str:
        return f"Visitor {self.face_id}"


class CapturedSnapshot(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    job_id = models.CharField(max_length=26, unique=True)
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
            models.Index(
                fields=["branch", "timestamp"], name="snapshot_branch_time_idx"
            ),
            models.Index(fields=["status", "timestamp"]),
            models.Index(fields=["visitor", "timestamp"]),
        ]

    def __str__(self) -> str:
        visitor = self.visitor.face_id if self.visitor else "unassigned"
        return f"{self.job_id} - {visitor} - {self.status}"
