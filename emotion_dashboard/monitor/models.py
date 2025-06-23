from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class UniqueFaceID(models.Model):
    face_id = models.CharField(max_length=255, primary_key=True)
    embedding = models.JSONField()

    class Meta:
        managed = False  # Tell Django NOT to manage this table
        db_table = 'unique_face_id'  # Exact name of the MySQL table


class Branch(models.Model):
    name = models.CharField(max_length=100)
    code_prefix = models.CharField(max_length=10, unique=True)  # e.g. 'FBLNUN'

    def __str__(self):
        return self.name
    
class UserProfile(models.Model):
    user = models.OneToOneField('CustomUser', on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    
    @property
    def is_superadmin(self):
        return self.user.is_superuser

class CustomUser(AbstractUser):
    branch = models.ForeignKey(
        Branch, 
        on_delete=models.PROTECT,  # Prevent branch deletion if users exist
        null=True,
        blank=True,
        verbose_name="Assigned Branch"
    )

    def save(self, *args, **kwargs):
        """Ensure superusers don't get branch assignments"""
        if self.is_superuser:
            self.branch = None
        super().save(*args, **kwargs)

class Emotion(models.Model):
    face = models.ForeignKey(UniqueFaceID, on_delete=models.CASCADE)
    detected_emotion = models.CharField(max_length=100)
    confidence = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"{self.face.face_id} - {self.detected_emotion}"

class Visit(models.Model):
    face_id = models.CharField(max_length=100, default="unknown")
    visit_time = models.DateTimeField()

    def __str__(self):
        return f"{self.face_id} - {self.visit_time}"

class VisitDetail(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE)
    image_path = models.TextField()

    def __str__(self):
        return f"Detail for {self.visit}"
    
class Visitor(models.Model):
    name = models.CharField(max_length=100)
    face_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class VisitLog(models.Model):
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE)
    emotion = models.CharField(max_length=50)
    timestamp = models.DateTimeField(default=timezone.now)
    branch = models.ForeignKey(
        Branch, 
        on_delete=models.CASCADE,
        related_name='visit_logs',
        null=False,  # Ensure branch is always required
        # Remove default=1 unless you are sure branch with pk=1 always exists
    )

    def __str__(self):
        return f"{self.visitor} - {self.emotion} at {self.timestamp}"