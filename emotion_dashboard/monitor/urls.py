from django.urls import path
from . import settings_views
from . import views


urlpatterns = [
    path(
        "",
        views.login_view,
        name="login",
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout",
    ),

    path(
        "dashboard/",
        views.dashboard,
        name="dashboard",
    ),

    path(
        "branches/",
        views.branch_overview,
        name="branch_overview",
    ),

    path(
        "branch/<int:branch_id>/",
        views.branch_detail,
        name="branch_detail",
    ),

    path(
        "emotion-analytics/",
        views.emotion_analytics,
        name="emotion_analytics",
    ),

    path(
        "reports/",
        views.reports,
        name="reports",
    ),

    path(
        "settings/",
        settings_views.settings_view,
        name="settings",
    ),

    path(
        "snapshot/<int:snapshot_id>/image/",
        views.snapshot_image,
        name="snapshot_image",
    ),
]