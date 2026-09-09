import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import (
    Count,
    F,
    IntegerField,
    Max,
    Min,
    OuterRef,
    Q,
    Subquery,
)
from django.db.models.functions import TruncDate
from django.http import (
    FileResponse,
    Http404,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .models import UserPreference, Visitor
from .tenant import (
    get_visible_branch_or_404,
    require_bank_admin,
    visible_branches,
    visible_snapshots,
)


EMOTIONS = (
    "happy",
    "neutral",
    "sad",
    "angry",
    "surprise",
)

EMOTION_COLORS = {
    "happy": "#FFD166",
    "neutral": "#8A8A8A",
    "sad": "#118AB2",
    "angry": "#EF476F",
    "surprise": "#8338EC",
    "none": "#6C757D",
}


class CSVBuffer:
    def write(self, value):
        return value


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get(
            "username",
            "",
        ).strip()

        password = request.POST.get(
            "password",
            "",
        )

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)

            next_url = request.GET.get(
                "next"
            )

            if (
                next_url
                and url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={
                        request.get_host()
                    },
                    require_https=(
                        request.is_secure()
                    ),
                )
            ):
                return redirect(next_url)

            return redirect("dashboard")

        messages.error(
            request,
            "Invalid username or password.",
        )

    return render(
        request,
        "registration/login.html",
    )


def logout_view(request):
    logout(request)

    return redirect("login")


def _date_window(value):
    end = timezone.localtime()

    days = {
        "day": 1,
        "week": 7,
        "month": 30,
        "14days": 14,
    }.get(value, 14)

    if days == 1:
        start = end.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

    else:
        start = end - timedelta(
            days=days - 1
        )

    return start, end, days


def _scoped_query(request):
    queryset = visible_snapshots(
        request.user
    )

    selected_branch = None

    if request.user.branch_id:
        selected_branch = (
            request.user.branch
        )

        return (
            queryset.filter(
                branch_id=(
                    request.user.branch_id
                )
            ),
            selected_branch,
        )

    branch_was_supplied = (
        "branch" in request.GET
        or "branch" in request.POST
    )

    branch_id = (
        request.GET.get("branch")
        or request.POST.get("branch")
    )

    if (
        not branch_was_supplied
        and request.method == "GET"
    ):
        preferences, _ = (
            UserPreference.objects
            .get_or_create(
                user=request.user
            )
        )

        branch_id = (
            preferences.default_branch_id
        )

    if branch_id:
        try:
            branch_id = int(
                branch_id
            )

        except (
            TypeError,
            ValueError,
        ):
            branch_id = None

    if branch_id:
        selected_branch = (
            visible_branches(
                request.user
            )
            .filter(
                pk=branch_id
            )
            .first()
        )

        if selected_branch:
            queryset = queryset.filter(
                branch_id=(
                    selected_branch.id
                )
            )

    return (
        queryset,
        selected_branch,
    )


def _emotion_counts(queryset):
    counts = {
        emotion: 0
        for emotion in EMOTIONS
    }

    grouped = (
        queryset
        .order_by()
        .exclude(
            emotion=""
        )
        .values(
            "emotion"
        )
        .annotate(
            total=Count("id")
        )
    )

    for item in grouped:
        emotion = item[
            "emotion"
        ]

        if emotion in counts:
            counts[emotion] = item[
                "total"
            ]

    return counts


def _trend_data(
    queryset,
    start,
    end,
):
    labels = []

    values = {
        emotion: []
        for emotion in EMOTIONS
    }

    grouped = (
        queryset
        .annotate(
            trend_date=TruncDate("timestamp")
        )
        .values("trend_date", "emotion")
        .annotate(total=Count("id"))
    )
    totals = {
        (row["trend_date"], row["emotion"]): row["total"]
        for row in grouped
    }
    current = start.date()

    while current <= end.date():
        labels.append(
            current.strftime(
                "%Y-%m-%d"
            )
        )

        for emotion in EMOTIONS:
            values[emotion].append(
                totals.get(
                    (current, emotion),
                    0,
                )
            )

        current += timedelta(
            days=1
        )

    datasets = [
        {
            "label": emotion.title(),

            "data": values[
                emotion
            ],

            "backgroundColor": (
                EMOTION_COLORS[
                    emotion
                ]
                + "80"
            ),

            "borderColor": (
                EMOTION_COLORS[
                    emotion
                ]
            ),

            "borderWidth": 2,
        }
        for emotion in EMOTIONS
    ]

    return labels, datasets


def _hourly_data(
    queryset,
    target_date,
):
    labels = [
        f"{hour:02d}:00"
        for hour in range(24)
    ]

    result = {
        emotion: [0] * 24
        for emotion in EMOTIONS
    }

    grouped = (
        queryset
        .filter(
            timestamp__date=(
                target_date
            )
        )
        .values(
            "timestamp__hour",
            "emotion",
        )
        .annotate(
            total=Count("id")
        )
    )

    for row in grouped:
        hour = row[
            "timestamp__hour"
        ]

        emotion = row[
            "emotion"
        ]

        if (
            emotion in result
            and hour is not None
        ):
            result[
                emotion
            ][hour] = row[
                "total"
            ]

    result[
        "labels"
    ] = labels

    return result


def _growth(
    queryset,
    negative=False,
):
    today = timezone.localdate()

    yesterday = (
        today
        - timedelta(
            days=1
        )
    )

    if negative:
        queryset = queryset.filter(
            emotion__in=(
                "sad",
                "angry",
            )
        )

        today_count = (
            queryset.filter(
                timestamp__date=today
            ).count()
        )

        yesterday_count = (
            queryset.filter(
                timestamp__date=yesterday
            ).count()
        )

    else:
        today_count = (
            queryset
            .filter(
                timestamp__date=today
            )
            .values(
                "visitor_id"
            )
            .distinct()
            .count()
        )

        yesterday_count = (
            queryset
            .filter(
                timestamp__date=(
                    yesterday
                )
            )
            .values(
                "visitor_id"
            )
            .distinct()
            .count()
        )

    if yesterday_count == 0:
        return (
            100
            if today_count
            else 0
        )

    return round(
        (
            (
                today_count
                - yesterday_count
            )
            / yesterday_count
        )
        * 100,
        1,
    )


@login_required
def dashboard(request):
    preferences, _ = (
        UserPreference.objects
        .get_or_create(
            user=request.user
        )
    )

    (
        scoped_all,
        selected_branch,
    ) = _scoped_query(
        request
    )

    time_range = (
        request.GET.get(
            "range"
        )
        or preferences.default_date_range
    )

    (
        start,
        end,
        trend_days,
    ) = _date_window(
        time_range
    )

    completed_queryset = (
        scoped_all.filter(
            status="done"
        )
    )

    period_queryset = (
        completed_queryset.filter(
            timestamp__range=(
                start,
                end,
            )
        )
    )

    (
        trend_labels,
        trend_datasets,
    ) = _trend_data(
        period_queryset,
        start,
        end,
    )

    hourly_range = (
        request.GET.get(
            "hourly"
        )
        or preferences.default_hourly_range
    )

    target_date = (
        timezone.localdate()
    )

    if hourly_range == "yesterday":
        target_date -= timedelta(
            days=1
        )

    hourly = _hourly_data(
        completed_queryset,
        target_date,
    )

    today_queryset = (
        completed_queryset.filter(
            timestamp__date=(
                timezone.localdate()
            )
        )
    )

    today_counts = (
        _emotion_counts(
            today_queryset
        )
    )

    total_detections = sum(
        today_counts.values()
    )

    (
        top_name,
        top_value,
    ) = max(
        today_counts.items(),
        key=lambda item: item[1],
    )

    negative_count = (
        today_counts["sad"]
        + today_counts["angry"]
    )

    hourly_totals = [
        sum(
            hourly[
                emotion
            ][index]
            for emotion in EMOTIONS
        )
        for index in range(24)
    ]

    if max(
        hourly_totals,
        default=0,
    ):
        peak_hour = (
            hourly_totals.index(
                max(
                    hourly_totals
                )
            )
        )

    else:
        peak_hour = None

    if selected_branch:
        branch_name = (
            selected_branch.name
        )

    elif request.user.is_superuser:
        branch_name = (
            "All Banks"
        )

    elif request.user.bank_id:
        branch_name = (
            request.user.bank.name
        )

    else:
        branch_name = (
            "No Bank Assigned"
        )

    context = {
        "branch_name": (
            branch_name
        ),

        "dashboard_preferences": (
            preferences
        ),

        "total_visitors": (
            today_queryset
            .values(
                "visitor_id"
            )
            .distinct()
            .count()
        ),

        "visitor_growth": (
            _growth(
                completed_queryset
            )
        ),

        "top_emotion": {
            "emotion": (
                top_name
                if top_value
                else "none"
            ),

            "percentage": (
                round(
                    (
                        top_value
                        / total_detections
                    )
                    * 100,
                    1,
                )
                if total_detections
                else 0
            ),
        },

        "negative_percentage": (
            round(
                (
                    negative_count
                    / total_detections
                )
                * 100,
                1,
            )
            if total_detections
            else 0
        ),

        "negative_growth": (
            _growth(
                completed_queryset,
                negative=True,
            )
        ),

        "activity_level": (
            "No Activity"
            if total_detections == 0
            else "Low"
            if total_detections < 10
            else "Moderate"
            if total_detections < 30
            else "High"
            if total_detections < 50
            else "Very High"
        ),

        "peak_time": (
            f"{peak_hour:02d}:00"
            if peak_hour is not None
            else "No data"
        ),

        "total_detections": (
            total_detections
        ),

        "emotion_labels": (
            json.dumps(
                list(
                    today_counts.keys()
                )
            )
        ),

        "emotion_data": (
            json.dumps(
                list(
                    today_counts.values()
                )
            )
        ),

        "emotion_colors": (
            json.dumps(
                [
                    EMOTION_COLORS[
                        emotion
                    ]
                    for emotion
                    in today_counts
                ]
            )
        ),

        "trend_labels": (
            json.dumps(
                trend_labels
            )
        ),

        "trend_datasets": (
            json.dumps(
                trend_datasets
            )
        ),

        "trend_days": (
            trend_days
        ),

        "time_range": (
            time_range
        ),

        "hourly_range": (
            hourly_range
        ),

        "hourly_labels": (
            json.dumps(
                hourly[
                    "labels"
                ]
            )
        ),

        "hourly_happy": (
            json.dumps(
                hourly[
                    "happy"
                ]
            )
        ),

        "hourly_neutral": (
            json.dumps(
                hourly[
                    "neutral"
                ]
            )
        ),

        "hourly_sad": (
            json.dumps(
                hourly[
                    "sad"
                ]
            )
        ),

        "hourly_angry": (
            json.dumps(
                hourly[
                    "angry"
                ]
            )
        ),

        "hourly_surprise": (
            json.dumps(
                hourly[
                    "surprise"
                ]
            )
        ),

        "branches": (
            visible_branches(
                request.user
            )
        ),

        "selected_branch": (
            str(
                selected_branch.id
            )
            if selected_branch
            else ""
        ),

        "is_superuser": (
            request.user.is_superuser
        ),
    }

    return render(
        request,
        "monitor/dashboard.html",
        context,
    )


@login_required
def branch_overview(request):
    require_bank_admin(
        request.user
    )

    time_range = (
        request.GET.get(
            "range",
            "week",
        )
    )

    (
        start,
        end,
        days,
    ) = _date_window(
        time_range
    )

    labels = [
        (
            start
            + timedelta(
                days=index
            )
        ).strftime(
            "%b %d"
        )
        for index in range(
            days
        )
    ]

    branches = list(
        visible_branches(
            request.user
        )
    )

    branch_ids = [
        branch.id
        for branch in branches
    ]

    period_snapshots = (
        visible_snapshots(
            request.user
        )
        .filter(
            branch_id__in=(
                branch_ids
            ),

            timestamp__range=(
                start,
                end,
            ),

            status="done",
        )
    )

    trend_rows = (
        period_snapshots
        .annotate(
            trend_date=TruncDate(
                "timestamp"
            )
        )
        .values(
            "branch_id",
            "trend_date",
        )
        .annotate(
            positive=Count(
                "id",
                filter=Q(
                    emotion="happy"
                ),
            ),

            negative=Count(
                "id",
                filter=Q(
                    emotion__in=(
                        "sad",
                        "angry",
                    )
                ),
            ),
        )
    )

    trend_by_branch = {}

    for row in trend_rows:
        trend_by_branch.setdefault(
            row[
                "branch_id"
            ],
            {},
        )[
            row[
                "trend_date"
            ]
        ] = (
            row[
                "positive"
            ]
            - row[
                "negative"
            ]
        )

    branch_summaries = []
    chart_datasets = []

    for branch in branches:
        queryset = (
            period_snapshots.filter(
                branch_id=branch.id
            )
        )

        counts = (
            _emotion_counts(
                queryset
            )
        )

        total = sum(
            counts.values()
        )

        top_emotion = (
            max(
                counts.items(),
                key=lambda item: (
                    item[1]
                ),
            )[0]
            if total
            else "none"
        )

        branch_trend = (
            trend_by_branch.get(
                branch.id,
                {},
            )
        )

        trend = [
            branch_trend.get(
                (
                    start
                    + timedelta(
                        days=index
                    )
                ).date(),
                0,
            )
            for index in range(
                days
            )
        ]

        display_name = (
            branch.name
        )

        if request.user.is_superuser:
            display_name = (
                f"{branch.bank.code} - "
                f"{branch.name}"
            )

        branch_summaries.append(
            {
                "id": branch.id,

                "name": (
                    display_name
                ),

                "visitor_count": (
                    queryset
                    .values(
                        "visitor_id"
                    )
                    .distinct()
                    .count()
                ),

                "top_emotion": (
                    top_emotion
                ),

                "positivity_percent": (
                    round(
                        (
                            counts[
                                "happy"
                            ]
                            / total
                        )
                        * 100,
                        1,
                    )
                    if total
                    else 0
                ),

                "trend_counts": (
                    trend
                ),
            }
        )

        chart_datasets.append(
            {
                "label": (
                    display_name
                ),

                "data": (
                    trend
                ),

                "borderWidth": 2,
                "tension": 0.3,
                "fill": False,
            }
        )

    return render(
        request,
        (
            "monitor/"
            "branch_overview.html"
        ),
        {
            "branches": (
                branch_summaries
            ),

            "time_range": (
                time_range
            ),

            "branch_chart_data": {
                "labels": (
                    labels
                ),

                "datasets": (
                    chart_datasets
                ),
            },
        },
    )


@login_required
def branch_detail(
    request,
    branch_id,
):
    branch = (
        get_visible_branch_or_404(
            request.user,
            branch_id,
        )
    )

    queryset = (
        visible_snapshots(
            request.user
        )
        .filter(
            branch_id=branch.id,
            status="done",
        )
    )

    counts = (
        _emotion_counts(
            queryset
        )
    )

    hourly = _hourly_data(
        queryset,
        timezone.localdate(),
    )

    hourly_visits = [
        sum(
            hourly[
                emotion
            ][index]
            for emotion in EMOTIONS
        )
        for index in range(24)
    ]

    hourly_positivity = [
        (
            round(
                (
                    hourly[
                        "happy"
                    ][index]
                    / hourly_visits[
                        index
                    ]
                )
                * 100,
                1,
            )
            if hourly_visits[
                index
            ]
            else 0
        )
        for index in range(24)
    ]

    emotion_distribution = [
        {
            "emotion": (
                emotion
            ),

            "count": (
                count
            ),
        }
        for (
            emotion,
            count,
        ) in counts.items()
    ]

    return render(
        request,
        (
            "monitor/"
            "branch_detail.html"
        ),
        {
            "branch": (
                branch
            ),

            "visits": (
                queryset[:20]
            ),

            "total_emotions": (
                queryset.count()
            ),

            "emotion_dist": (
                emotion_distribution
            ),

            "emotion_labels": (
                json.dumps(
                    [
                        emotion.title()
                        for emotion
                        in counts
                    ]
                )
            ),

            "emotion_counts": (
                json.dumps(
                    list(
                        counts.values()
                    )
                )
            ),

            "emotion_colors": (
                json.dumps(
                    [
                        EMOTION_COLORS[
                            emotion
                        ]
                        for emotion
                        in counts
                    ]
                )
            ),

            "hourly_labels": (
                json.dumps(
                    hourly[
                        "labels"
                    ]
                )
            ),

            "hourly_visits": (
                json.dumps(
                    hourly_visits
                )
            ),

            "hourly_positivity": (
                json.dumps(
                    hourly_positivity
                )
            ),
        },
    )


@login_required
def emotion_analytics(request):
    (
        scoped_queryset,
        _,
    ) = _scoped_query(
        request
    )

    time_range = (
        request.GET.get(
            "range",
            "week",
        )
    )

    (
        start,
        end,
        _,
    ) = _date_window(
        time_range
    )

    period_queryset = (
        scoped_queryset.filter(
            timestamp__range=(
                start,
                end,
            ),

            status="done",
        )
    )

    counts = _emotion_counts(
        period_queryset
    )

    (
        labels,
        datasets,
    ) = _trend_data(
        period_queryset,
        start,
        end,
    )

    hourly = _hourly_data(
        scoped_queryset.filter(
            status="done"
        ),
        timezone.localdate(),
    )

    hourly_total = [
        sum(
            hourly[
                emotion
            ][index]
            for emotion in EMOTIONS
        )
        for index in range(24)
    ]

    branch_comparison = []

    for branch in visible_branches(
        request.user
    ):
        branch_queryset = (
            period_queryset.filter(
                branch_id=branch.id
            )
        )

        branch_counts = (
            _emotion_counts(
                branch_queryset
            )
        )

        total = sum(
            branch_counts.values()
        )

        branch_comparison.append(
            {
                "name": (
                    branch.name
                ),

                "happy": (
                    round(
                        (
                            branch_counts[
                                "happy"
                            ]
                            / total
                        )
                        * 100,
                        1,
                    )
                    if total
                    else 0
                ),

                "neutral": (
                    round(
                        (
                            branch_counts[
                                "neutral"
                            ]
                            / total
                        )
                        * 100,
                        1,
                    )
                    if total
                    else 0
                ),

                "negative": (
                    round(
                        (
                            (
                                branch_counts[
                                    "sad"
                                ]
                                + branch_counts[
                                    "angry"
                                ]
                            )
                            / total
                        )
                        * 100,
                        1,
                    )
                    if total
                    else 0
                ),

                "total_visits": (
                    branch_queryset
                    .values(
                        "visitor_id"
                    )
                    .distinct()
                    .count()
                ),
            }
        )

    return render(
        request,
        (
            "monitor/"
            "emotion_analytics.html"
        ),
        {
            "page_title": (
                "Emotion Analytics"
            ),

            "chart_data": {
                "labels": (
                    labels
                ),

                "datasets": (
                    datasets
                ),
            },

            "hourly_labels": (
                json.dumps(
                    hourly[
                        "labels"
                    ]
                )
            ),

            "hourly_data": (
                json.dumps(
                    hourly_total
                )
            ),

            "dist_labels": (
                json.dumps(
                    list(
                        counts.keys()
                    )
                )
            ),

            "dist_data": (
                json.dumps(
                    list(
                        counts.values()
                    )
                )
            ),

            "dist_colors": (
                json.dumps(
                    [
                        EMOTION_COLORS[
                            emotion
                        ]
                        for emotion
                        in counts
                    ]
                )
            ),

            "time_range": (
                time_range
            ),

            "branch_comparison": (
                branch_comparison
            ),
        },
    )


def _visitor_scope_label(user):
    if user.branch_id:
        return user.branch.name

    if user.bank_id:
        return user.bank.name

    if user.is_superuser:
        return "All banks"

    return "No bank assigned"


@login_required
def visitor_list(request):
    """List visitors using only snapshots visible to the current tenant user."""
    scoped_snapshots = visible_snapshots(request.user).filter(status="done")
    latest_snapshot = (
        scoped_snapshots
        .filter(visitor_id=OuterRef("pk"))
        .order_by("-timestamp", "-id")
    )
    visit_totals = (
        scoped_snapshots
        .filter(visitor_id=OuterRef("pk"))
        .order_by()
        .values("visitor_id")
        .annotate(total=Count("id"))
        .values("total")[:1]
    )
    visitors = (
        Visitor.objects
        .filter(pk__in=scoped_snapshots.values("visitor_id"))
        .annotate(
            scoped_last_seen=Subquery(
                latest_snapshot.values("timestamp")[:1]
            ),
            last_emotion=Subquery(
                latest_snapshot.values("emotion")[:1]
            ),
            latest_snapshot_id=Subquery(
                latest_snapshot.values("id")[:1]
            ),
            latest_image_path=Subquery(
                latest_snapshot.values("image_path")[:1]
            ),
            visit_count=Subquery(
                visit_totals,
                output_field=IntegerField(),
            ),
        )
        .order_by("-scoped_last_seen", "face_id")
    )

    search_query = request.GET.get("search", "").strip()
    if search_query:
        visitors = visitors.filter(face_id__icontains=search_query)

    page = Paginator(visitors, 25).get_page(request.GET.get("page"))
    for visitor in page.object_list:
        visitor.last_seen = visitor.scoped_last_seen
        visitor.visit_count = visitor.visit_count or 0
        visitor.initials = (visitor.face_id[:2] or "?").upper()
        visitor.image_url = (
            reverse("snapshot_image", args=[visitor.latest_snapshot_id])
            if visitor.latest_snapshot_id and visitor.latest_image_path
            else ""
        )

    return render(
        request,
        "monitor/visitors.html",
        {
            "visitors": page,
            "search_query": search_query,
            "branch_name": _visitor_scope_label(request.user),
        },
    )


@login_required
def visitor_detail(request, visitor_id):
    """Show a visitor profile without exposing out-of-scope snapshots."""
    scoped_snapshots = (
        visible_snapshots(request.user)
        .filter(visitor_id=visitor_id, status="done")
        .order_by("-timestamp", "-id")
    )
    visitor = get_object_or_404(
        Visitor.objects.filter(
            pk=visitor_id,
            pk__in=scoped_snapshots.values("visitor_id"),
        )
    )
    summary = scoped_snapshots.aggregate(
        first_seen=Min("timestamp"),
        last_seen=Max("timestamp"),
    )
    emotion_counts = _emotion_counts(scoped_snapshots)
    total_visits = scoped_snapshots.count()
    detected_emotion_count = sum(
        1 for count in emotion_counts.values() if count
    )
    most_frequent_emotion = (
        max(emotion_counts.items(), key=lambda item: item[1])[0]
        if detected_emotion_count
        else "none"
    )
    emotion_percentages = {
        emotion: (
            round((count / total_visits) * 100, 1)
            if total_visits
            else 0
        )
        for emotion, count in emotion_counts.items()
    }
    first_seen = summary["first_seen"]
    last_seen = summary["last_seen"]
    visit_frequency = None
    if first_seen and last_seen and total_visits > 1:
        active_days = max((last_seen.date() - first_seen.date()).days + 1, 1)
        visit_frequency = f"{round(total_visits / active_days, 1)} visits per day"

    latest_snapshot = scoped_snapshots.first()
    image_url = (
        reverse("snapshot_image", args=[latest_snapshot.id])
        if latest_snapshot and latest_snapshot.image_path
        else ""
    )

    return render(
        request,
        "monitor/visitor_detail.html",
        {
            "visitor": visitor,
            "image_url": image_url,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "total_visits": total_visits,
            "detected_emotion_count": detected_emotion_count,
            "emotion_counts": emotion_counts,
            "emotion_percentages": emotion_percentages,
            "most_frequent_emotion": most_frequent_emotion,
            "positive_percent": emotion_percentages["happy"],
            "negative_percent": round(
                emotion_percentages["sad"] + emotion_percentages["angry"],
                1,
            ),
            "visit_frequency": visit_frequency,
            "average_duration": None,
            "chart_labels": json.dumps(
                [emotion.title() for emotion in emotion_counts]
            ),
            "chart_values": json.dumps(list(emotion_counts.values())),
            "chart_colors": json.dumps(
                [EMOTION_COLORS[emotion] for emotion in emotion_counts]
            ),
        },
    )


@login_required
def visit_history(request):
    """Show and export tenant-scoped daily visit activity."""
    snapshots = visible_snapshots(request.user).filter(status="done")
    face_id = request.GET.get("face_id", "").strip()
    selected_emotion = request.GET.get("emotion", "").strip().lower()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    if face_id:
        snapshots = snapshots.filter(visitor__face_id__icontains=face_id)
    if selected_emotion in EMOTIONS:
        snapshots = snapshots.filter(emotion=selected_emotion)
    else:
        selected_emotion = ""

    for value, lookup in (
        (date_from, "timestamp__date__gte"),
        (date_to, "timestamp__date__lte"),
    ):
        if not value:
            continue
        try:
            parsed_date = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            if lookup.endswith("gte"):
                date_from = ""
            else:
                date_to = ""
            continue
        snapshots = snapshots.filter(**{lookup: parsed_date})

    grouped_visits = (
        snapshots
        .annotate(
            face_id=F("visitor__face_id"),
            visit_date=TruncDate("timestamp"),
        )
        .values(
            "visitor_id",
            "face_id",
            "visit_date",
            "branch__name",
        )
        .annotate(
            first_visit=Min("timestamp"),
            last_visit=Max("timestamp"),
            visit_count=Count("id"),
        )
        .order_by("-visit_date", "-last_visit", "face_id")
    )

    if request.GET.get("export", "").lower() == "true":
        writer = csv.writer(CSVBuffer())

        def csv_rows():
            yield writer.writerow(
                ["Face ID", "Date", "First visit", "Last visit", "Visits", "Branch"]
            )
            for visit in grouped_visits.iterator(chunk_size=1000):
                yield writer.writerow(
                    [
                        visit["face_id"],
                        visit["visit_date"].isoformat(),
                        visit["first_visit"].isoformat(),
                        visit["last_visit"].isoformat(),
                        visit["visit_count"],
                        visit["branch__name"],
                    ]
                )

        response = StreamingHttpResponse(csv_rows(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="visit-history.csv"'
        return response

    page = Paginator(grouped_visits, 50).get_page(request.GET.get("page"))
    return render(
        request,
        "monitor/visit_history.html",
        {
            "visits": page,
            "face_id": face_id,
            "selected_emotion": selected_emotion,
            "date_from": date_from,
            "date_to": date_to,
        },
    )


@login_required
def reports(request):
    branches = visible_branches(
        request.user
    )

    if request.method == "POST":
        (
            queryset,
            _,
        ) = _scoped_query(
            request
        )

        try:
            date_from = (
                datetime.strptime(
                    request.POST[
                        "date_from"
                    ],
                    "%Y-%m-%d",
                ).date()
            )

            date_to = (
                datetime.strptime(
                    request.POST[
                        "date_to"
                    ],
                    "%Y-%m-%d",
                ).date()
            )

        except (
            KeyError,
            ValueError,
        ):
            messages.error(
                request,
                (
                    "Choose a valid "
                    "date range."
                ),
            )

            return redirect(
                "reports"
            )

        queryset = (
            queryset
            .filter(
                timestamp__date__range=(
                    date_from,
                    date_to,
                )
            )
            .order_by(
                "timestamp"
            )
        )

        writer = csv.writer(
            CSVBuffer()
        )

        def csv_rows():
            yield writer.writerow(
                [
                    "Bank",
                    "Branch",
                    "Visitor ID",
                    "PC",
                    "Emotion",
                    "Confidence",
                    "Timestamp",
                ]
            )

            for snapshot in (
                queryset.iterator(
                    chunk_size=1000
                )
            ):
                yield writer.writerow(
                    [
                        snapshot.bank.name,

                        snapshot.branch.name,

                        snapshot.visitor.face_id,

                        snapshot.pc_name,

                        snapshot.emotion,

                        snapshot.confidence,

                        snapshot.timestamp.isoformat(),
                    ]
                )

        response = (
            StreamingHttpResponse(
                csv_rows(),
                content_type=(
                    "text/csv"
                ),
            )
        )

        response[
            "Content-Disposition"
        ] = (
            "attachment; "
            f'filename="sentiment-'
            f'{date_from}-{date_to}.csv"'
        )

        return response

    return render(
        request,
        "monitor/reports.html",
        {
            "branches": (
                branches
            ),
        },
    )


@login_required
def snapshot_image(
    request,
    snapshot_id,
):
    """
    Protect captured images using the same tenant restrictions
    used for dashboard records.
    """
    snapshot = (
        visible_snapshots(
            request.user
        )
        .filter(
            pk=snapshot_id
        )
        .first()
    )

    if not snapshot:
        raise Http404

    root = Path(
        settings.CAPTURED_FACES_ROOT
    ).resolve()

    image_path = (
        root
        / snapshot.image_path
    ).resolve()

    # Prevent ../../ path traversal.
    if root not in image_path.parents:
        raise Http404

    if not image_path.is_file():
        raise Http404

    return FileResponse(
        image_path.open(
            "rb"
        ),
        content_type=(
            "image/jpeg"
        ),
    )
