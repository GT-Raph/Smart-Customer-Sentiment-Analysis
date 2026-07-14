from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Bank,
    BankSettings,
    Branch,
    CapturedSnapshot,
    CustomUser,
    UserPreference,
    Visitor,
)


class SuperuserOnlyAdminMixin:
    """
    Restrict this Django Admin section to platform
    superusers only.

    Normal bank administrators use the application's
    Settings page instead of Django Admin.
    """

    def has_module_permission(
        self,
        request,
    ):
        return (
            request.user.is_active
            and request.user.is_superuser
        )

    def has_view_permission(
        self,
        request,
        obj=None,
    ):
        return (
            request.user.is_active
            and request.user.is_superuser
        )

    def has_add_permission(
        self,
        request,
    ):
        return (
            request.user.is_active
            and request.user.is_superuser
        )

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return (
            request.user.is_active
            and request.user.is_superuser
        )

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return (
            request.user.is_active
            and request.user.is_superuser
        )


@admin.register(Bank)
class BankAdmin(
    SuperuserOnlyAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "code",
        "is_active",
        "api_key_configured",
        "api_key_rotated_at",
        "created_at",
    )

    list_filter = (
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "code",
    )

    ordering = (
        "name",
    )

    readonly_fields = (
        "api_key_hash",
        "api_key_rotated_at",
        "created_at",
    )

    fieldsets = (
        (
            "Bank details",
            {
                "fields": (
                    "name",
                    "code",
                    "is_active",
                )
            },
        ),
        (
            "Upload API security",
            {
                "fields": (
                    "api_key_hash",
                    "api_key_rotated_at",
                ),

                "description": (
                    "The API key is stored only as a hash. "
                    "Generate or rotate it from the application "
                    "Settings page or the management command."
                ),
            },
        ),
        (
            "System information",
            {
                "fields": (
                    "created_at",
                )
            },
        ),
    )

    @admin.display(
        boolean=True,
        description="API key configured",
    )
    def api_key_configured(
        self,
        obj,
    ):
        return obj.has_api_key


@admin.register(Branch)
class BranchAdmin(
    SuperuserOnlyAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "bank",
        "code",
        "pc_prefix",
        "location",
        "is_active",
    )

    list_filter = (
        "bank",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "pc_prefix",
        "location",
        "bank__name",
        "bank__code",
    )

    autocomplete_fields = (
        "bank",
    )

    ordering = (
        "bank__name",
        "name",
    )

    fieldsets = (
        (
            "Branch details",
            {
                "fields": (
                    "bank",
                    "name",
                    "code",
                    "location",
                    "is_active",
                )
            },
        ),
        (
            "Computer-name matching",
            {
                "fields": (
                    "pc_prefix",
                ),

                "description": (
                    "Captures are assigned to this branch when "
                    "the Windows computer name begins with this "
                    "prefix. Example: prefix FBLRGE matches "
                    "FBLRGE001 and FBLRGE002."
                ),
            },
        ),
    )


@admin.register(CustomUser)
class CustomUserAdmin(
    SuperuserOnlyAdminMixin,
    UserAdmin,
):
    list_display = (
        "username",
        "email",
        "bank",
        "branch",
        "access_level",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "bank",
        "branch",
        "groups",
    )

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "bank__name",
        "branch__name",
    )

    ordering = (
        "username",
    )

    autocomplete_fields = (
        "bank",
        "branch",
    )

    fieldsets = (
        UserAdmin.fieldsets
        + (
            (
                "Bank access",
                {
                    "fields": (
                        "bank",
                        "branch",
                    ),

                    "description": (
                        "Leave Branch empty for a bank "
                        "administrator. Select a Branch to "
                        "restrict the user to that specific "
                        "branch."
                    ),
                },
            ),
        )
    )

    add_fieldsets = (
        UserAdmin.add_fieldsets
        + (
            (
                "Bank access",
                {
                    "classes": (
                        "wide",
                    ),

                    "fields": (
                        "email",
                        "first_name",
                        "last_name",
                        "bank",
                        "branch",
                        "is_active",
                        "is_staff",
                        "is_superuser",
                    ),
                },
            ),
        )
    )

    @admin.display(
        description="Access level",
    )
    def access_level(
        self,
        obj,
    ):
        if obj.is_superuser:
            return (
                "Platform administrator"
            )

        if obj.branch_id:
            return "Branch user"

        if obj.bank_id:
            return (
                "Bank administrator"
            )

        return "Unassigned"


@admin.register(UserPreference)
class UserPreferenceAdmin(
    SuperuserOnlyAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "user",
        "default_date_range",
        "default_hourly_range",
        "default_branch",
        "auto_refresh_seconds",
        "notify_negative",
        "updated_at",
    )

    list_filter = (
        "default_date_range",
        "default_hourly_range",
        "auto_refresh_seconds",
        "compact_mode",
        "reduce_motion",
        "notify_negative",
        "email_weekly_summary",
    )

    search_fields = (
        "user__username",
        "user__email",
        "user__bank__name",
        "default_branch__name",
    )

    autocomplete_fields = (
        "user",
        "default_branch",
    )

    readonly_fields = (
        "updated_at",
    )

    fieldsets = (
        (
            "User",
            {
                "fields": (
                    "user",
                )
            },
        ),
        (
            "Dashboard defaults",
            {
                "fields": (
                    "default_date_range",
                    "default_hourly_range",
                    "default_branch",
                    "auto_refresh_seconds",
                    "compact_mode",
                    "reduce_motion",
                )
            },
        ),
        (
            "Notifications",
            {
                "fields": (
                    "email_weekly_summary",
                    "notify_negative",
                    "negative_threshold",
                    "minimum_detections",
                )
            },
        ),
        (
            "System information",
            {
                "fields": (
                    "updated_at",
                )
            },
        ),
    )


@admin.register(BankSettings)
class BankSettingsAdmin(
    SuperuserOnlyAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "bank",
        "timezone",
        "image_retention_days",
        "record_retention_days",
        "delete_images_after_retention",
        "offline_after_minutes",
        "updated_at",
    )

    list_filter = (
        "timezone",
        "delete_images_after_retention",
    )

    search_fields = (
        "bank__name",
        "bank__code",
    )

    autocomplete_fields = (
        "bank",
    )

    readonly_fields = (
        "updated_at",
    )

    fieldsets = (
        (
            "Bank",
            {
                "fields": (
                    "bank",
                    "timezone",
                )
            },
        ),
        (
            "Data retention",
            {
                "fields": (
                    "image_retention_days",
                    "record_retention_days",
                    "delete_images_after_retention",
                )
            },
        ),
        (
            "Capture status",
            {
                "fields": (
                    "offline_after_minutes",
                )
            },
        ),
        (
            "System information",
            {
                "fields": (
                    "updated_at",
                )
            },
        ),
    )


@admin.register(Visitor)
class VisitorAdmin(
    SuperuserOnlyAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "face_id",
        "bank",
        "first_seen",
        "last_seen",
    )

    list_filter = (
        "bank",
        "first_seen",
        "last_seen",
    )

    search_fields = (
        "face_id",
        "bank__name",
        "bank__code",
    )

    autocomplete_fields = (
        "bank",
    )

    readonly_fields = (
        "first_seen",
        "last_seen",
    )

    ordering = (
        "-last_seen",
    )


@admin.register(CapturedSnapshot)
class CapturedSnapshotAdmin(
    SuperuserOnlyAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "job_id",
        "bank",
        "branch",
        "visitor",
        "pc_name",
        "emotion",
        "confidence",
        "status",
        "timestamp",
    )

    list_filter = (
        "bank",
        "branch",
        "emotion",
        "status",
        "processed",
        "timestamp",
    )

    search_fields = (
        "job_id",
        "pc_name",
        "visitor__face_id",
        "bank__name",
        "bank__code",
        "branch__name",
        "branch__code",
    )

    autocomplete_fields = (
        "bank",
        "branch",
        "visitor",
    )

    readonly_fields = (
        "job_id",
        "bank",
        "branch",
        "visitor",
        "pc_name",
        "image_path",
        "timestamp",
        "emotion",
        "confidence",
        "emotion_vector",
        "embedding",
        "processed",
        "status",
        "processing_error",
    )

    ordering = (
        "-timestamp",
    )

    date_hierarchy = "timestamp"

    fieldsets = (
        (
            "Capture identity",
            {
                "fields": (
                    "job_id",
                    "bank",
                    "branch",
                    "visitor",
                    "pc_name",
                    "timestamp",
                )
            },
        ),
        (
            "Emotion result",
            {
                "fields": (
                    "emotion",
                    "confidence",
                    "emotion_vector",
                )
            },
        ),
        (
            "Face-processing result",
            {
                "fields": (
                    "embedding",
                    "image_path",
                    "processed",
                    "status",
                    "processing_error",
                )
            },
        ),
    )

    def has_add_permission(
        self,
        request,
    ):
        # Snapshots must come from the authenticated face API,
        # not from manual Django Admin entry.
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        # Captured evidence remains read-only in Admin.
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        # Captured evidence cannot be deleted in Admin.
        return False