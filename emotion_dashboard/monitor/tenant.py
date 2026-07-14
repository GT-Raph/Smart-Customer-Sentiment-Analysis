from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Branch, CapturedSnapshot, Visitor


def visible_branches(user):
    """
    Return only branches the authenticated user is allowed to see.
    """
    queryset = Branch.objects.filter(
        is_active=True
    ).select_related("bank")

    if user.is_superuser:
        return queryset

    if not user.bank_id:
        return queryset.none()

    queryset = queryset.filter(
        bank_id=user.bank_id
    )

    if user.branch_id:
        queryset = queryset.filter(
            pk=user.branch_id
        )

    return queryset


def visible_snapshots(user):
    """
    Return only snapshots the authenticated user is allowed to see.
    """
    queryset = CapturedSnapshot.objects.select_related(
        "bank",
        "branch",
        "visitor",
    )

    if user.is_superuser:
        return queryset

    if not user.bank_id:
        return queryset.none()

    queryset = queryset.filter(
        bank_id=user.bank_id
    )

    if user.branch_id:
        queryset = queryset.filter(
            branch_id=user.branch_id
        )

    return queryset


def visible_visitors(user):
    queryset = Visitor.objects.select_related("bank")

    if user.is_superuser:
        return queryset

    if not user.bank_id:
        return queryset.none()

    return queryset.filter(
        bank_id=user.bank_id
    )


def get_visible_branch_or_404(user, branch_id):
    return get_object_or_404(
        visible_branches(user),
        pk=branch_id,
    )


def require_bank_admin(user):
    """
    A branch user cannot open the branch-comparison page.
    """
    if user.is_superuser:
        return

    if not user.bank_id or user.branch_id:
        raise PermissionDenied