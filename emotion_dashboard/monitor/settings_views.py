from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .access import visible_branches
from .forms import (
    BranchSettingsForm,
    DashboardPreferenceForm,
    NotificationPreferenceForm,
    ProfileSettingsForm,
    StyledPasswordChangeForm,
)
from .models import Branch, Device, UserPreference


def _forms_for(user, preferences):
    return {
        "profile_form": ProfileSettingsForm(instance=user, prefix="profile"),
        "dashboard_form": DashboardPreferenceForm(
            instance=preferences, user=user, prefix="dashboard"
        ),
        "notification_form": NotificationPreferenceForm(
            instance=preferences, prefix="notifications"
        ),
        "password_form": StyledPasswordChangeForm(user=user, prefix="password"),
    }


def _computer_rows(user):
    devices = (
        Device.objects.filter(branch__in=visible_branches(user))
        .select_related("branch")
        .annotate(total_captures=Count("snapshots"))
        .order_by("branch__name", "pc_name")
    )
    cutoff = timezone.now() - timedelta(minutes=15)
    return [
        {
            "pc_name": device.pc_name,
            "branch__name": device.branch.name,
            "branch__pc_prefix": device.branch.pc_prefix,
            "last_seen": device.last_seen_at,
            "total_captures": device.total_captures,
            "is_online": bool(
                device.is_active
                and device.last_seen_at
                and device.last_seen_at >= cutoff
            ),
            "status": (
                "Online"
                if device.is_active
                and device.last_seen_at
                and device.last_seen_at >= cutoff
                else "Offline"
            ),
        }
        for device in devices
    ]


@login_required
def settings_view(request):
    preferences, _ = UserPreference.objects.get_or_create(user=request.user)
    forms = _forms_for(request.user, preferences)
    bound_branch_form = None
    bound_branch_id = None

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "profile":
            forms["profile_form"] = ProfileSettingsForm(
                request.POST, instance=request.user, prefix="profile"
            )
            if forms["profile_form"].is_valid():
                forms["profile_form"].save()
                messages.success(request, "Your profile was updated.")
                return redirect("settings")

        elif action == "dashboard":
            forms["dashboard_form"] = DashboardPreferenceForm(
                request.POST,
                instance=preferences,
                user=request.user,
                prefix="dashboard",
            )
            if forms["dashboard_form"].is_valid():
                forms["dashboard_form"].save()
                messages.success(request, "Dashboard preferences were saved.")
                return redirect("settings")

        elif action == "notifications":
            forms["notification_form"] = NotificationPreferenceForm(
                request.POST, instance=preferences, prefix="notifications"
            )
            if forms["notification_form"].is_valid():
                forms["notification_form"].save()
                messages.success(request, "Notification preferences were saved.")
                return redirect("settings")

        elif action == "password":
            forms["password_form"] = StyledPasswordChangeForm(
                user=request.user, data=request.POST, prefix="password"
            )
            if forms["password_form"].is_valid():
                user = forms["password_form"].save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password was changed successfully.")
                return redirect("settings")

        elif action == "branch_settings" and request.user.can_manage_all_branches:
            branch = get_object_or_404(Branch, pk=request.POST.get("branch_id"))
            bound_branch_id = branch.id
            bound_branch_form = BranchSettingsForm(
                request.POST, instance=branch, prefix=f"branch-{branch.id}"
            )
            if bound_branch_form.is_valid():
                bound_branch_form.save()
                messages.success(request, f"{branch.name} was updated.")
                return redirect("settings")

        else:
            messages.error(request, "Unknown or unauthorized settings action.")

    branch_rows = []
    if request.user.can_manage_all_branches:
        for branch in Branch.objects.order_by("name"):
            form = (
                bound_branch_form
                if bound_branch_id == branch.id and bound_branch_form
                else BranchSettingsForm(instance=branch, prefix=f"branch-{branch.id}")
            )
            branch_rows.append({"branch": branch, "form": form})

    preference_branches = forms["dashboard_form"].fields[
        "default_branch"
    ].queryset
    context = {
        **forms,
        "preferences": preferences,
        "preference_branches": preference_branches,
        "branch_rows": branch_rows,
        "computer_rows": _computer_rows(request.user),
        "can_manage_branches": request.user.can_manage_all_branches,
    }
    return render(request, "monitor/settings.html", context)
