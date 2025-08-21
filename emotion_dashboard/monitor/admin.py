from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser, Branch, UserProfile

# ------------------------------ Branch Admin ---------------------------------
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code_prefix', 'user_count')
    search_fields = ('name', 'code_prefix')
    list_per_page = 20

    def user_count(self, obj):
        return obj.customuser_set.count()
    user_count.short_description = 'Users'

    class Meta:
        verbose_name = "Branch"
        verbose_name_plural = "Branches"

# ----------------------------- Custom User Admin -----------------------------
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'branch', 'is_staff', 'is_active')
    list_filter = ('branch', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    list_per_page = 20
    actions = ['activate_users', 'deactivate_users']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Branch Info', {'fields': ('branch',)}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'branch', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(branch=request.user.branch) if request.user.branch else qs.none()

    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_users.short_description = "Deactivate selected users"

# ---------------------------- Final Registration -----------------------------
admin.site.register(CustomUser, CustomUserAdmin)