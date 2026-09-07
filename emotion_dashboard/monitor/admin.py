from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Branch,
    CapturedSnapshot,
    CustomUser,
    Device,
    UserPreference,
    UserProfile,
    Visitor,
)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "pc_prefix", "location", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "pc_prefix", "location")


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "branch", "pc_name", "is_active", "last_seen_at")
    list_filter = ("branch", "is_active")
    search_fields = ("name", "pc_name", "api_key_prefix")
    readonly_fields = ("api_key_prefix", "created_at", "last_seen_at")
    exclude = ("api_key_hash",)


class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "branch", "is_staff", "is_active")
    list_filter = ("branch", "is_staff", "is_superuser", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Dashboard access", {"fields": ("branch",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Dashboard access", {"fields": ("branch",)}),
    )


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserProfile)
admin.site.register(UserPreference)
admin.site.register(Visitor)


@admin.register(CapturedSnapshot)
class CapturedSnapshotAdmin(admin.ModelAdmin):
    list_display = ("job_id", "branch", "device", "status", "emotion", "timestamp")
    list_filter = ("branch", "status", "emotion")
    search_fields = ("job_id", "pc_name", "visitor__face_id")
    readonly_fields = (
        "job_id",
        "branch",
        "device",
        "visitor",
        "pc_name",
        "session_id",
        "image_path",
        "upload_content_type",
        "upload_size_bytes",
        "timestamp",
        "status",
        "emotion",
        "confidence",
        "emotion_vector",
        "processed",
        "embedding",
        "error_message",
        "processed_at",
    )
