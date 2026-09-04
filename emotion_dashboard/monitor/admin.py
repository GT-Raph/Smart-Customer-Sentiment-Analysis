from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Branch,
    CapturedSnapshot,
    CustomUser,
    Device,
    Organization,
    MonthlyUsage,
    UserProfile,
    Visitor,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "plan", "subscription_status", "monthly_analysis_limit", "is_active")
    search_fields = ("name", "slug", "billing_customer_reference")
    list_filter = ("plan", "subscription_status", "is_active")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "pc_prefix", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "organization__name", "pc_prefix")


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "branch", "pc_name", "is_active", "last_seen_at")
    list_filter = ("organization", "branch", "is_active")
    search_fields = ("name", "pc_name", "api_key_prefix")
    readonly_fields = ("api_key_prefix", "created_at", "last_seen_at")
    exclude = ("api_key_hash",)


class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "organization", "branch", "is_staff", "is_active")
    list_filter = ("organization", "branch", "is_staff", "is_superuser", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Tenant access", {"fields": ("organization", "branch")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Tenant access", {"fields": ("organization", "branch")}),
    )


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserProfile)
admin.site.register(Visitor)


@admin.register(CapturedSnapshot)
class CapturedSnapshotAdmin(admin.ModelAdmin):
    list_display = ("job_id", "organization", "branch", "device", "status", "emotion", "timestamp")
    list_filter = ("organization", "branch", "status", "emotion")
    search_fields = ("job_id", "pc_name", "visitor__face_id")
    readonly_fields = (
        "job_id",
        "organization",
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


@admin.register(MonthlyUsage)
class MonthlyUsageAdmin(admin.ModelAdmin):
    list_display = ("organization", "period_start", "analyses_count", "updated_at")
    list_filter = ("organization", "period_start")
    readonly_fields = ("organization", "period_start", "analyses_count", "updated_at")
