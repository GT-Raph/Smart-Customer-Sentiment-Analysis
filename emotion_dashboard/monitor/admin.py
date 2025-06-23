from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser, Branch, UniqueFaceID, Emotion, Visit, VisitDetail, Visitor, VisitLog

# ---------------------------- UniqueFaceID Admin -----------------------------
@admin.register(UniqueFaceID)
class UniqueFaceIDAdmin(admin.ModelAdmin):
    list_display = ('face_id', 'embedding_preview')
    readonly_fields = ('face_id', 'embedding', 'embedding_preview')
    list_per_page = 20
    search_fields = ('face_id',)

    def embedding_preview(self, obj):
        return format_html('<code>{:.50}...</code>', str(obj.embedding))
    embedding_preview.short_description = 'Embedding Preview'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

# ------------------------------ Branch Admin ---------------------------------
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code_prefix', 'user_count')
    search_fields = ('name', 'code_prefix')
    list_per_page = 20
    
    def user_count(self, obj):
        return obj.customuser_set.count()
    user_count.short_description = 'Users'

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

# ------------------------------ VisitLog Admin -------------------------------
@admin.register(VisitLog)
class VisitLogAdmin(admin.ModelAdmin):
    list_display = ('visitor', 'emotion', 'timestamp', 'branch_info')
    list_filter = ('emotion', 'branch', 'timestamp')
    search_fields = ('visitor__face_id', 'emotion')
    date_hierarchy = 'timestamp'
    list_per_page = 30

    def branch_info(self, obj):
        return obj.branch.name if obj.branch else '-'
    branch_info.short_description = 'Branch'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser and request.user.branch:
            return qs.filter(branch=request.user.branch)
        return qs

# ---------------------------- VisitDetail Inline -----------------------------
class VisitDetailInline(admin.TabularInline):
    model = VisitDetail
    extra = 0
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        return format_html('<img src="{}" height="50" />', obj.image_path)
    image_preview.short_description = 'Preview'

# ------------------------------- Visit Admin ---------------------------------
@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('face_id', 'visit_time', 'emotion_summary')
    search_fields = ('face_id',)
    list_filter = ('visit_time',)
    inlines = [VisitDetailInline]
    list_per_page = 20

    def emotion_summary(self, obj):
        emotions = Emotion.objects.filter(face__face_id=obj.face_id)
        return emotions.first().detected_emotion if emotions.exists() else '-'
    emotion_summary.short_description = 'Primary Emotion'

# ------------------------------ Emotion Admin --------------------------------
@admin.register(Emotion)
class EmotionAdmin(admin.ModelAdmin):
    list_display = ('face', 'detected_emotion', 'confidence', 'timestamp')
    search_fields = ('face__face_id', 'detected_emotion')
    list_filter = ('detected_emotion', 'timestamp')
    readonly_fields = ('confidence',)
    list_per_page = 30

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser and request.user.branch:
            return qs.filter(face__face_id__startswith=request.user.branch.code_prefix)
        return qs

# ---------------------------- VisitDetail Admin ------------------------------
@admin.register(VisitDetail)
class VisitDetailAdmin(admin.ModelAdmin):
    list_display = ('visit', 'image_preview', 'emotion_info', 'timestamp_info')
    search_fields = ('visit__face_id',)
    readonly_fields = ('image_preview',)
    list_per_page = 20

    def image_preview(self, obj):
        return format_html('<img src="{}" height="50" />', obj.image_path)
    image_preview.short_description = 'Image'

    def emotion_info(self, obj):
        return obj.visit.emotion_summary()
    emotion_info.short_description = 'Emotion'

    def timestamp_info(self, obj):
        return obj.visit.visit_time
    timestamp_info.short_description = 'Timestamp'

# ---------------------------- Final Registration -----------------------------
admin.site.register(CustomUser, CustomUserAdmin)