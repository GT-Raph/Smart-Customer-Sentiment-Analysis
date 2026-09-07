"""Branch-level access helpers for the single-installation edition."""

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .models import Branch, CapturedSnapshot, Visitor


def visible_branches(user):
    queryset = Branch.objects.filter(is_active=True)
    if user.is_superuser:
        return queryset
    if not user.branch_id:
        return queryset.none()
    return queryset.filter(pk=user.branch_id)


def visible_snapshots(user):
    queryset = CapturedSnapshot.objects.select_related("branch", "device", "visitor")
    if user.is_superuser:
        return queryset
    if not user.branch_id or not user.branch.is_active:
        return queryset.none()
    return queryset.filter(branch_id=user.branch_id)


def visible_visitors(user):
    queryset = Visitor.objects.all()
    if user.is_superuser:
        return queryset
    if not user.branch_id or not user.branch.is_active:
        return queryset.none()
    return queryset.filter(snapshots__branch_id=user.branch_id).distinct()


def get_visible_branch_or_404(user, branch_id):
    return get_object_or_404(visible_branches(user), pk=branch_id)


def require_branch_manager(user):
    if not user.can_manage_all_branches:
        raise PermissionDenied("Only an administrator can compare all branches.")
