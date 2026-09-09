import secrets
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import (
    update_session_auth_hash,
)
from django.contrib.auth.decorators import (
    login_required,
)
from django.core.exceptions import (
    PermissionDenied,
)
from django.db.models import (
    Count,
    Max,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone

from .forms import (
    BankSettingsForm,
    BranchSettingsForm,
    DashboardPreferenceForm,
    NotificationPreferenceForm,
    ProfileSettingsForm,
    StyledPasswordChangeForm,
)
from .models import (
    Bank,
    BankSettings,
    UserPreference,
)
from .tenant import (
    visible_branches,
    visible_snapshots,
)


def _visible_banks(user):
    queryset = Bank.objects.filter(
        is_active=True
    ).order_by("name")

    if user.is_superuser:
        return queryset

    if user.bank_id:
        return queryset.filter(
            pk=user.bank_id
        )

    return queryset.none()


def _manageable_bank_or_404(
    user,
    bank_id,
):
    if not user.is_bank_admin:
        raise PermissionDenied

    queryset = _visible_banks(user)

    return get_object_or_404(
        queryset,
        pk=bank_id,
    )


def _manageable_branch_or_404(
    user,
    branch_id,
):
    if not user.is_bank_admin:
        raise PermissionDenied

    return get_object_or_404(
        visible_branches(user),
        pk=branch_id,
    )


def _computer_rows(
    user,
    bank_settings_map,
):
    group_fields = (
        "bank_id",
        "bank__name",
        "branch_id",
        "branch__name",
        "branch__pc_prefix",
        "pc_name",
    )
    snapshots = visible_snapshots(user)
    lifetime_rows = list(
        snapshots
        .values(
            *group_fields,
        )
        .annotate(
            total_captures=Count("id"),
            lifetime_last_seen=Max("timestamp"),
        )
    )
    current_time = timezone.now()
    maximum_offline_minutes = max(
        [
            15,
            *(
                item.offline_after_minutes
                for item in bank_settings_map.values()
            ),
        ]
    )
    recent_rows = (
        snapshots
        .filter(
            timestamp__gte=(
                current_time
                - timedelta(minutes=maximum_offline_minutes)
            )
        )
        .values(*group_fields)
        .annotate(recent_last_seen=Max("timestamp"))
    )
    recent_by_computer = {
        tuple(row[field] for field in group_fields): row["recent_last_seen"]
        for row in recent_rows
    }
    computer_rows = []

    for row in lifetime_rows:
        computer_key = tuple(row[field] for field in group_fields)
        recent_last_seen = recent_by_computer.get(computer_key)
        settings_object = (
            bank_settings_map.get(
                row["bank_id"]
            )
        )

        offline_minutes = (
            settings_object
            .offline_after_minutes
            if settings_object
            else 15
        )

        cutoff = (
            current_time
            - timedelta(
                minutes=offline_minutes
            )
        )

        is_online = bool(
            recent_last_seen
            and recent_last_seen >= cutoff
        )

        computer_rows.append(
            {
                **row,

                "last_seen": row["lifetime_last_seen"],

                "is_online": is_online,

                "status": (
                    "Online"
                    if is_online
                    else "Offline"
                ),

                "offline_minutes": (
                    offline_minutes
                ),
            }
        )

    computer_rows.sort(
        key=lambda row: (
            row["last_seen"] is not None,
            row["last_seen"] or current_time,
        ),
        reverse=True,
    )

    return computer_rows


@login_required
def settings_view(request):
    preferences, _ = (
        UserPreference.objects
        .get_or_create(
            user=request.user
        )
    )

    profile_form = ProfileSettingsForm(
        instance=request.user,
        prefix="profile",
    )

    dashboard_form = (
        DashboardPreferenceForm(
            instance=preferences,
            user=request.user,
            prefix="dashboard",
        )
    )

    notification_form = (
        NotificationPreferenceForm(
            instance=preferences,
            prefix="notifications",
        )
    )

    password_form = (
        StyledPasswordChangeForm(
            user=request.user,
            prefix="password",
        )
    )

    bound_bank_form = None
    bound_bank_id = None

    bound_branch_form = None
    bound_branch_id = None

    if request.method == "POST":
        action = request.POST.get(
            "action",
            "",
        )

        if action == "profile":
            profile_form = (
                ProfileSettingsForm(
                    request.POST,
                    instance=request.user,
                    prefix="profile",
                )
            )

            if profile_form.is_valid():
                profile_form.save()

                messages.success(
                    request,
                    "Your profile was updated.",
                )

                return redirect("settings")

        elif action == "dashboard":
            dashboard_form = (
                DashboardPreferenceForm(
                    request.POST,
                    instance=preferences,
                    user=request.user,
                    prefix="dashboard",
                )
            )

            if dashboard_form.is_valid():
                dashboard_form.save()

                messages.success(
                    request,
                    (
                        "Dashboard preferences "
                        "were saved."
                    ),
                )

                return redirect("settings")

        elif action == "notifications":
            notification_form = (
                NotificationPreferenceForm(
                    request.POST,
                    instance=preferences,
                    prefix="notifications",
                )
            )

            if notification_form.is_valid():
                notification_form.save()

                messages.success(
                    request,
                    (
                        "Notification preferences "
                        "were saved."
                    ),
                )

                return redirect("settings")

        elif action == "password":
            password_form = (
                StyledPasswordChangeForm(
                    user=request.user,
                    data=request.POST,
                    prefix="password",
                )
            )

            if password_form.is_valid():
                updated_user = (
                    password_form.save()
                )

                update_session_auth_hash(
                    request,
                    updated_user,
                )

                messages.success(
                    request,
                    (
                        "Your password was "
                        "changed successfully."
                    ),
                )

                return redirect("settings")

        elif action == "bank_settings":
            bank_id = request.POST.get(
                "bank_id"
            )

            bank = (
                _manageable_bank_or_404(
                    request.user,
                    bank_id,
                )
            )

            settings_object, _ = (
                BankSettings.objects
                .get_or_create(
                    bank=bank
                )
            )

            bound_bank_id = bank.id

            bound_bank_form = (
                BankSettingsForm(
                    request.POST,
                    instance=settings_object,
                    prefix=(
                        f"bank-{bank.id}"
                    ),
                )
            )

            if bound_bank_form.is_valid():
                bound_bank_form.save()

                messages.success(
                    request,
                    (
                        f"Settings for "
                        f"{bank.name} were saved."
                    ),
                )

                return redirect("settings")

        elif action == "branch_settings":
            branch_id = request.POST.get(
                "branch_id"
            )

            branch = (
                _manageable_branch_or_404(
                    request.user,
                    branch_id,
                )
            )

            bound_branch_id = branch.id

            bound_branch_form = (
                BranchSettingsForm(
                    request.POST,
                    instance=branch,
                    prefix=(
                        f"branch-{branch.id}"
                    ),
                )
            )

            if bound_branch_form.is_valid():
                bound_branch_form.save()

                messages.success(
                    request,
                    (
                        f"{branch.name} was "
                        f"updated."
                    ),
                )

                return redirect("settings")

        elif action == "rotate_api_key":
            bank_id = request.POST.get(
                "bank_id"
            )

            bank = (
                _manageable_bank_or_404(
                    request.user,
                    bank_id,
                )
            )

            raw_api_key = (
                secrets.token_urlsafe(32)
            )

            bank.set_api_key(
                raw_api_key
            )

            bank.save(
                update_fields=[
                    "api_key_hash",
                    "api_key_rotated_at",
                ]
            )

            request.session[
                "new_bank_api_key"
            ] = {
                "bank_name": bank.name,
                "bank_code": bank.code,
                "raw_key": raw_api_key,
            }

            messages.warning(
                request,
                (
                    "The old API key has been "
                    "disabled. Update every capture "
                    "computer for this bank."
                ),
            )

            return redirect("settings")

        else:
            messages.error(
                request,
                "Unknown settings action.",
            )

    banks = list(
        _visible_banks(
            request.user
        )
    )

    bank_settings_map = {}
    bank_rows = []

    for bank in banks:
        settings_object, _ = (
            BankSettings.objects
            .get_or_create(
                bank=bank
            )
        )

        bank_settings_map[
            bank.id
        ] = settings_object

        if (
            bound_bank_id == bank.id
            and bound_bank_form
        ):
            form = bound_bank_form

        else:
            form = BankSettingsForm(
                instance=settings_object,
                prefix=f"bank-{bank.id}",
            )

        bank_rows.append(
            {
                "bank": bank,
                "settings": settings_object,
                "form": form,
            }
        )

    branch_rows = []

    for branch in visible_branches(
        request.user
    ):
        if (
            bound_branch_id == branch.id
            and bound_branch_form
        ):
            form = bound_branch_form

        else:
            form = BranchSettingsForm(
                instance=branch,
                prefix=(
                    f"branch-{branch.id}"
                ),
            )

        branch_rows.append(
            {
                "branch": branch,
                "form": form,
            }
        )

    computer_rows = _computer_rows(
        request.user,
        bank_settings_map,
    )

    new_api_key = (
        request.session.pop(
            "new_bank_api_key",
            None,
        )
    )

    context = {
        "profile_form": profile_form,

        "dashboard_form": (
            dashboard_form
        ),

        "notification_form": (
            notification_form
        ),

        "password_form": password_form,

        "preferences": preferences,

        "preference_branches": (
            dashboard_form.fields[
                "default_branch"
            ].queryset
        ),

        "bank_rows": bank_rows,

        "branch_rows": branch_rows,

        "computer_rows": computer_rows,

        "can_manage_bank": (
            request.user.is_bank_admin
        ),

        "new_api_key": new_api_key,
    }

    return render(
        request,
        "monitor/settings.html",
        context,
    )
