from django.db import models
from django.contrib.auth.models import AbstractUser


class Branch(models.Model):
    name = models.CharField(max_length=100)
    pc_prefix = models.CharField(
        max_length=50,
        unique=True,
        help_text="PC name prefix for this branch"
    )
    location = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Branch"
        verbose_name_plural = "Branches"

    def __str__(self):
        return f"{self.name} ({self.pc_prefix})"

    @property
    def code_prefix(self):
        """For admin compatibility: alias for pc_prefix."""
        return self.pc_prefix

class CustomUser(AbstractUser):
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Assigned Branch"
    )

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.branch = None
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        # Add this if you want to use a different table name
        # db_table = 'monitor_userprofile'
        pass
    
    @property
    def is_superadmin(self):
        return self.user.is_superuser
    
    @property
    def pc_prefix(self):
        """Return the PC prefix from the associated branch"""
        if self.branch:
            return self.branch.pc_prefix  # Fixed from code_prefix to pc_prefix
        return None
    
    def __str__(self):
        if self.branch:
            return f"{self.user.username} - {self.branch.name}"
        return f"{self.user.username} - No Branch"


class Visitor(models.Model):
    """Represents a unique visitor detected by the system."""
    face_id = models.CharField(max_length=128, unique=True)
    first_seen = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Visitor {self.face_id}"



class CapturedSnapshot(models.Model):
    """Snapshots tied to a visitor."""
    id = models.AutoField(primary_key=True)
    visitor = models.ForeignKey(Visitor, to_field="face_id", db_column="face_id", on_delete=models.CASCADE)
    pc_name = models.CharField(max_length=128)
    image_path = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    emotion = models.CharField(max_length=32, null=True, blank=True)
    processed = models.BooleanField(default=False)
    embedding = models.JSONField(null=True, blank=True)

    class Meta:
        managed = False  # Don’t let Django re-create the table
        db_table = 'captured_snapshots'

    def __str__(self):
        return f"Visitor {self.visitor.face_id} ({self.emotion}) on {self.pc_name}"
        return f"Visitor {self.visitor.face_id} ({self.emotion}) on {self.pc_name}"
