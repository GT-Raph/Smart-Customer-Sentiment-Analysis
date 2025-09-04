from django.http import HttpResponse
from django.db.models import Count
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
# from . import models
from .models import Branch, CapturedSnapshot
from datetime import timedelta, datetime
import json
from django.core.exceptions import PermissionDenied
from django.contrib.auth import authenticate, login
from django.db.models import Count
import json
from datetime import datetime, timedelta


# Use the recommended emotion color mapping everywhere
EMOTION_COLORS = {
    "happy":   {"border": "#FFD166", "background": "rgba(255,209,102,0.15)"},   # Sunshine Yellow
    "sad":     {"border": "#118AB2", "background": "rgba(17,138,178,0.15)"},    # Cool Blue
    "angry":   {"border": "#EF476F", "background": "rgba(239,71,111,0.15)"},    # Fiery Red
    "neutral": {"border": "#8A8A8A", "background": "rgba(138,138,138,0.15)"},   # Balanced Gray
    "surprise":{"border": "#8338EC", "background": "rgba(131,56,236,0.15)"},    # Vibrant Purple
    "none":    {"border": "#8A8A8A", "background": "rgba(138,138,138,0.15)"},   # fallback to gray
    "unknown": {"border": "#8A8A8A", "background": "rgba(138,138,138,0.15)"},   # fallback to gray
}


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")  # Redirect to dashboard after successful login
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, "registration/login.html")  # Always render login page

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')


@login_required
def dashboard(request):
    """
    Dashboard view:
    - Superuser: show combined data from ALL branches by default, with ability to filter by ?branch=...
    - Normal users: show only their assigned branch
    """
    branch_filter = request.GET.get('branch', None)

    if request.user.is_superuser:
        # ✅ If superuser selects a branch → filter by that branch
        # ✅ If not → combine ALL branches
        user_pc_prefix = branch_filter if branch_filter else None
    else:
        # ✅ Regular users → only their assigned branch
        user_pc_prefix = get_user_pc_prefix(request.user)

    # Get all active branches for superuser dropdown
    branches = []
    if request.user.is_superuser:
        branches = Branch.objects.filter(is_active=True).values('id', 'name', 'pc_prefix')

    # Get date range parameters
    time_range = request.GET.get('range', '14days')
    hourly_range = request.GET.get('hourly', 'today')

    # Calculate date ranges
    end_date = timezone.now()
    if time_range == 'day':
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        trend_days = 1
    elif time_range == 'week':
        start_date = end_date - timedelta(days=7)
        trend_days = 7
    elif time_range == 'month':
        start_date = end_date - timedelta(days=30)
        trend_days = 30
    else:  # 14days default
        start_date = end_date - timedelta(days=14)
        trend_days = 14

    # Get data from database
    emotion_data = get_emotion_data(user_pc_prefix, start_date, end_date)
    hourly_data = get_hourly_data(user_pc_prefix, hourly_range)

    # Get today's data for the summary cards
    today = timezone.now().date()

    # ✅ Unique visitors today
    if request.user.is_superuser:
        user_pc_prefix = request.GET.get('branch', None)
        # Show total visitors across all branches for superadmin
        if not user_pc_prefix:
            total_visitors_today = CapturedSnapshot.objects.filter(
                timestamp__date=today
            ).values("visitor__face_id").distinct().count()
        else:
            total_visitors_today = CapturedSnapshot.objects.filter(
                timestamp__date=today,
                pc_name__startswith=user_pc_prefix
            ).values("visitor__face_id").distinct().count()
    else:
        user_pc_prefix = get_user_pc_prefix(request.user)
        total_visitors_today = CapturedSnapshot.objects.filter(
            timestamp__date=today,
            pc_name__startswith=user_pc_prefix
        ).values("visitor__face_id").distinct().count()

    # ✅ Top emotion today
    emotion_counts_today = CapturedSnapshot.objects.filter(timestamp__date=today)
    if user_pc_prefix:
        emotion_counts_today = emotion_counts_today.filter(pc_name__startswith=user_pc_prefix)
    emotion_counts_today = (
        emotion_counts_today
        .values("emotion")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    if emotion_counts_today:
        top_emotion_today = {
            "emotion": emotion_counts_today[0]["emotion"],
            "percentage": round((emotion_counts_today[0]["total"] / sum(e["total"] for e in emotion_counts_today)) * 100, 1),
        }
    else:
        top_emotion_today = {"emotion": "none", "percentage": 0}

    # ✅ Negative emotions today (neutral is NOT negative)
    negative_emotions_today = sum(
        e["total"] for e in emotion_counts_today 
        if e["emotion"] in ['sad', 'angry']  # neutral is not included
    )
    total_detections_today = sum(e["total"] for e in emotion_counts_today)
    negative_percentage_today = round((negative_emotions_today / total_detections_today * 100), 1) if total_detections_today > 0 else 0

    # Define emotion colors for charts
    emotion_colors = {
        'happy': '#FFD166',
        'sad': '#118AB2', 
        'angry': '#EF476F',
        'neutral': '#8A8A8A',
        'surprise': '#8338EC',
        'none': '#6C757D'
    }

    # Prepare emotion distribution data with colors
    emotion_labels = list(emotion_data['emotion_counts'].keys())
    emotion_values = list(emotion_data['emotion_counts'].values())
    emotion_color_values = [emotion_colors.get(emotion, '#6C757D') for emotion in emotion_labels]

    # Prepare trend datasets with colors
    for dataset in emotion_data['trend_datasets']:
        emotion = dataset['label'].lower()
        dataset['backgroundColor'] = emotion_colors.get(emotion, '#6C757D') + '80'  # Add transparency
        dataset['borderColor'] = emotion_colors.get(emotion, '#6C757D')
        dataset['borderWidth'] = 2

    context = {
        'branch_name': (branch_filter or "All Branches") if request.user.is_superuser else (user_pc_prefix or "Unknown"),
        'total_visitors': total_visitors_today,
        'visitor_growth': calculate_growth(user_pc_prefix),
        'top_emotion': top_emotion_today,
        'negative_percentage': negative_percentage_today,
        'negative_growth': calculate_negative_growth(user_pc_prefix),
        'activity_level': get_activity_level(total_visitors_today),
        'peak_time': get_peak_time(hourly_data),
        'total_detections': total_detections_today,
        'emotion_labels': json.dumps(emotion_labels),
        'emotion_data': json.dumps(emotion_values),
        'emotion_colors': json.dumps(emotion_color_values),
        'trend_labels': json.dumps(emotion_data['trend_labels']),
        'trend_datasets': json.dumps(emotion_data['trend_datasets']),
        'trend_days': trend_days,
        'time_range': time_range,
        'hourly_range': hourly_range,
        'hourly_labels': json.dumps(hourly_data['labels']),
        'hourly_happy': json.dumps(hourly_data['happy']),
        'hourly_neutral': json.dumps(hourly_data['neutral']),
        'hourly_sad': json.dumps(hourly_data['sad']),
        'hourly_angry': json.dumps(hourly_data['angry']),
        'hourly_surprise': json.dumps(hourly_data['surprise']),
        'branches': branches,  # Superuser dropdown
        'selected_branch': branch_filter,  # Track selection
        'is_superuser': request.user.is_superuser,  # Flag
    }

    return render(request, 'monitor/dashboard.html', context)


def get_user_pc_prefix(user):
    """
    Get the PC name prefix for the current user
    This should be implemented based on how you store user-branch relationships
    """
    # Check if user has a profile with pc_prefix
    if hasattr(user, 'profile') and hasattr(user.profile, 'pc_prefix'):
        return user.profile.pc_prefix
    
    # Check if user has a branch relationship
    if hasattr(user, 'branch') and user.branch:
        return user.branch.pc_prefix  # Adjust based on your Branch model
    
    return None

def get_emotion_data(pc_prefix, start_date, end_date):
    """
    Get emotion data filtered by PC prefix and date range
    """
    # Build base query
    query = CapturedSnapshot.objects.filter(timestamp__range=(start_date, end_date))
    
    # Apply PC prefix filter if provided
    if pc_prefix:
        query = query.filter(pc_name__startswith=pc_prefix)
    
    # Get total visitors (unique face_ids)
    total_visitors = query.values('visitor__face_id').distinct().count()
    
    # Get total detections
    total_detections = query.count()
    
    # Get emotion counts
    emotion_counts_query = query.exclude(emotion__isnull=True)\
                               .values('emotion')\
                               .annotate(count=Count('id'))\
                               .order_by('-count')
    
    # Process emotion counts
    emotion_counts = {'happy': 0, 'sad': 0, 'angry': 0, 'neutral': 0, 'surprise': 0}
    for item in emotion_counts_query:
        if item['emotion'] in emotion_counts:
            emotion_counts[item['emotion']] = item['count']
    
    # Calculate top emotion
    top_emotion = max(emotion_counts.items(), key=lambda x: x[1])
    top_emotion_percentage = (top_emotion[1] / total_detections * 100) if total_detections > 0 else 0
    
    # Calculate negative emotions percentage (neutral is NOT negative)
    negative_emotions = emotion_counts['sad'] + emotion_counts['angry']
    negative_percentage = (negative_emotions / total_detections * 100) if total_detections > 0 else 0
    
    # Get trend data
    trend_data = get_trend_data(pc_prefix, start_date, end_date)
    
    return {
        'total_visitors': total_visitors,
        'total_detections': total_detections,
        'emotion_counts': emotion_counts,
        'top_emotion': {'emotion': top_emotion[0], 'percentage': round(top_emotion_percentage, 1)},
        'negative_percentage': round(negative_percentage, 1),
        'trend_labels': trend_data['labels'],
        'trend_datasets': trend_data['datasets']
    }

def get_trend_data(pc_prefix, start_date, end_date):
    """
    Get emotion trend data for the chart using Django ORM
    """
    # Generate date range
    date_range = []
    current_date = start_date.date()
    end_date_date = end_date.date()
    
    while current_date <= end_date_date:
        date_range.append(current_date.strftime('%Y-%m-%d'))
        current_date += timedelta(days=1)
    
    # Get daily counts for each emotion
    emotions = ['happy', 'sad', 'angry', 'neutral', 'surprise']
    datasets = []
    colors = ['#2ecc71', '#3498db', '#e74c3c', '#f1c40f', '#9b59b6']
    
    for i, emotion in enumerate(emotions):
        daily_counts = []
        for date_str in date_range:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = CapturedSnapshot.objects.filter(
                timestamp__date=date_obj,
                emotion=emotion
            )
            
            if pc_prefix:
                query = query.filter(pc_name__startswith=pc_prefix)
            
            count = query.count()
            daily_counts.append(count)
        
        datasets.append({
            'label': emotion.title(),
            'data': daily_counts,
            'backgroundColor': colors[i],
            'borderColor': colors[i],
            'borderWidth': 1
        })
    
    return {'labels': date_range, 'datasets': datasets}

def get_hourly_data(pc_prefix, range_type):
    """
    Get hourly emotion data using Django ORM
    """
    # Determine date filter
    if range_type == 'yesterday':
        target_date = (timezone.now() - timedelta(days=1)).date()
    else:  # today
        target_date = timezone.now().date()
    
    # Get hourly counts for each emotion
    hours = list(range(24))
    emotions = ['happy', 'neutral', 'sad', 'angry', 'surprise']
    result = {'labels': [f"{h:02d}:00" for h in hours]}
    
    for emotion in emotions:
        hourly_counts = []
        for hour in hours:
            query = CapturedSnapshot.objects.filter(
                timestamp__date=target_date,
                timestamp__hour=hour,
                emotion=emotion
            )
            if pc_prefix:
                query = query.filter(pc_name__startswith=pc_prefix)
            count = query.count()
            hourly_counts.append(count)
        
        result[emotion] = hourly_counts
    
    return result

def get_activity_level(total_visitors):
    """Determine activity level based on visitor count"""
    if total_visitors == 0:
        return "No Activity"
    elif total_visitors < 10:
        return "Low"
    elif total_visitors < 30:
        return "Moderate"
    elif total_visitors < 50:
        return "High"
    else:
        return "Very High"

def get_peak_time(hourly_data):
    """Find the hour with the most activity"""
    total_by_hour = [
        sum(hourly_data[emotion][i] for emotion in ['happy', 'neutral', 'sad', 'angry', 'surprise']) 
        for i in range(24)
    ]
    
    if max(total_by_hour) == 0:
        return "No data"
    
    peak_hour = total_by_hour.index(max(total_by_hour))
    return f"{peak_hour:02d}:00"

def calculate_growth(pc_prefix):
    """Calculate growth percentage from previous period"""
    # Implement actual growth calculation based on your business logic
    # This is a placeholder implementation
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    # Get today's count
    query_today = CapturedSnapshot.objects.filter(timestamp__date=today)
    if pc_prefix:
        query_today = query_today.filter(pc_name__startswith=pc_prefix)
    today_count = query_today.values('visitor__face_id').distinct().count()
    
    # Get yesterday's count
    query_yesterday = CapturedSnapshot.objects.filter(timestamp__date=yesterday)
    if pc_prefix:
        query_yesterday = query_yesterday.filter(pc_name__startswith=pc_prefix)
    yesterday_count = query_yesterday.values('visitor__face_id').distinct().count()
    
    if yesterday_count == 0:
        return 100 if today_count > 0 else 0
    
    growth = ((today_count - yesterday_count) / yesterday_count) * 100
    return round(growth, 1)

def calculate_negative_growth(pc_prefix):
    """Calculate negative emotions growth percentage"""
    # Implement actual negative growth calculation
    # This is a placeholder implementation
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    # Get today's negative emotions (neutral is NOT negative)
    query_today = CapturedSnapshot.objects.filter(
        timestamp__date=today,
        emotion__in=['sad', 'angry']
    )
    if pc_prefix:
        query_today = query_today.filter(pc_name__startswith=pc_prefix)
    today_negative = query_today.count()
    
    # Get yesterday's negative emotions (neutral is NOT negative)
    query_yesterday = CapturedSnapshot.objects.filter(
        timestamp__date=yesterday,
        emotion__in=['sad', 'angry']
    )
    if pc_prefix:
        query_yesterday = query_yesterday.filter(pc_name__startswith=pc_prefix)
    yesterday_negative = query_yesterday.count()
    
    if yesterday_negative == 0:
        return 100 if today_negative > 0 else 0
    
    growth = ((today_negative - yesterday_negative) / yesterday_negative) * 100
    return round(growth, 1)

@login_required
def branch_overview(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    branches = Branch.objects.filter(is_active=True)
    time_range = request.GET.get('range', 'week')
    if time_range == 'day':
        days = 1
    elif time_range == 'month':
        days = 30
    else:  # default to week
        days = 7

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days-1)
    date_labels = [(start_date + timedelta(days=i)).strftime('%b %d') for i in range(days)]

    branch_summaries = []
    chart_datasets = []

    # Define a color palette for branches (can be extended as needed)
    BRANCH_COLORS = [
        {"border": "#3498db", "background": "rgba(52, 152, 219, 0.1)"},  # Blue
        {"border": "#e74c3c", "background": "rgba(231, 76, 60, 0.1)"},   # Red
        {"border": "#2ecc71", "background": "rgba(46, 204, 113, 0.1)"},  # Green
        {"border": "#f39c12", "background": "rgba(243, 156, 18, 0.1)"},  # Orange
        {"border": "#9b59b6", "background": "rgba(155, 89, 182, 0.1)"},  # Purple
        {"border": "#1abc9c", "background": "rgba(26, 188, 156, 0.1)"},  # Teal
        {"border": "#d35400", "background": "rgba(211, 84, 0, 0.1)"},    # Dark Orange
        {"border": "#c0392b", "background": "rgba(192, 57, 43, 0.1)"},   # Dark Red
        {"border": "#16a085", "background": "rgba(22, 160, 133, 0.1)"},  # Dark Teal
        {"border": "#8e44ad", "background": "rgba(142, 68, 173, 0.1)"},  # Dark Purple
        {"border": "#27ae60", "background": "rgba(39, 174, 96, 0.1)"},   # Dark Green
        {"border": "#2980b9", "background": "rgba(41, 128, 185, 0.1)"},  # Dark Blue
    ]

    for idx, branch in enumerate(branches):
        pc_prefix = branch.pc_prefix

        visitor_count = CapturedSnapshot.objects.filter(
            pc_name__startswith=pc_prefix,
            timestamp__range=(start_date, end_date)
        ).values('visitor__face_id').distinct().count()

        emotion_counts = (
            CapturedSnapshot.objects.filter(
                pc_name__startswith=pc_prefix,
                timestamp__range=(start_date, end_date)
            )
            .values('emotion')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        top_emotion = emotion_counts[0]['emotion'] if emotion_counts else 'none'

        total = sum(e['count'] for e in emotion_counts)
        happy = next((e['count'] for e in emotion_counts if e['emotion'] == 'happy'), 0)
        positivity_score = (happy / total) if total > 0 else 0
        positivity_percent = round(positivity_score * 100, 1)

        trend_counts = []
        for date_str in [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            qs = CapturedSnapshot.objects.filter(
                pc_name__startswith=pc_prefix,
                timestamp__date=date_obj
            )
            pos = qs.filter(emotion='happy').count()
            neg = qs.filter(emotion__in=['sad', 'angry']).count()
            net = pos - neg
            trend_counts.append(net)

        # Use branch index to get a unique color, cycle through palette if needed
        color_idx = idx % len(BRANCH_COLORS)
        branch_color = BRANCH_COLORS[color_idx]

        branch_summaries.append({
            'id': branch.id,
            'name': branch.name,
            'visitor_count': visitor_count,
            'top_emotion': top_emotion,
            'positivity_score': positivity_score,
            'positivity_percent': positivity_percent,
            'trend_counts': trend_counts,
            'color': branch_color,  # Store color for template use if needed
        })

        chart_datasets.append({
            "label": branch.name,
            "data": trend_counts,
            "borderColor": branch_color["border"],
            "backgroundColor": branch_color["background"],
            "pointBackgroundColor": branch_color["border"],
            "pointBorderColor": "#fff",
            "pointHoverBackgroundColor": "#fff",
            "pointHoverBorderColor": branch_color["border"],
            "pointRadius": 4,
            "pointHoverRadius": 6,
            "tension": 0.4,
            "fill": True,
            "borderWidth": 3,
        })

    context = {
        "branches": branch_summaries,
        "time_range": time_range,
        "chart_labels": json.dumps(date_labels),
        "chart_datasets": json.dumps(chart_datasets),
    }
    return render(request, "monitor/branch_overview.html", context)

@login_required
def reports(request):
    context = {
        'page_title': 'Reports',
        # Add your reports data here
    }
    return render(request, 'monitor/reports.html', context)

@login_required
def settings(request):
    context = {
        'page_title': 'Settings',
        # Add your settings data here
    }
    return render(request, 'monitor/settings.html', context)

@login_required
def branch_detail(request, branch_id):
    try:
        branch = Branch.objects.get(pk=branch_id)
    except Branch.DoesNotExist:
        return HttpResponse("Branch not found.", status=404)

    if not request.user.is_superuser:
        user_branch = getattr(request.user, "branch", None)
        if not user_branch or user_branch.id != branch.id:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You do not have permission to view this branch.")

    pc_prefix = branch.pc_prefix

    # Get recent visits
    visits = CapturedSnapshot.objects.filter(
        pc_name__startswith=pc_prefix
    ).select_related('visitor').order_by('-timestamp')[:20]
    
    total_emotions = CapturedSnapshot.objects.filter(pc_name__startswith=pc_prefix).count()

    # Get emotion distribution
    from django.db.models import Count
    emotion_dist = (
        CapturedSnapshot.objects.filter(pc_name__startswith=pc_prefix)
        .values('emotion')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    
    # Define emotion colors
    EMOTION_COLORS = {
        'happy': {'border': '#FFD166', 'background': 'rgba(255, 209, 102, 0.2)'},
        'neutral': {'border': '#8A8A8A', 'background': 'rgba(138, 138, 138, 0.2)'},
        'sad': {'border': '#118AB2', 'background': 'rgba(17, 138, 178, 0.2)'},
        'angry': {'border': '#EF476F', 'background': 'rgba(239, 71, 111, 0.2)'},
        'surprise': {'border': '#8338EC', 'background': 'rgba(131, 56, 236, 0.2)'},
        'none': {'border': '#6C757D', 'background': 'rgba(108, 117, 125, 0.2)'},
        'unknown': {'border': '#6C757D', 'background': 'rgba(108, 117, 125, 0.2)'}
    }

    # Prepare emotion data for chart
    emotion_labels = []
    emotion_counts = []
    emotion_colors = []
    
    for e in emotion_dist:
        emotion_name = e['emotion'] or 'unknown'
        emotion_labels.append(emotion_name.title())
        emotion_counts.append(e['count'])
        emotion_colors.append(EMOTION_COLORS.get(emotion_name.lower(), EMOTION_COLORS['unknown'])['border'])

    # Hourly activity data
    hours = list(range(24))
    hourly_labels = [f"{h:02d}:00" for h in hours]
    hourly_visits = []
    hourly_positivity = []

    for hour in hours:
        # Get visits for this hour
        hour_visits = CapturedSnapshot.objects.filter(
            pc_name__startswith=pc_prefix,
            timestamp__hour=hour
        )
        
        count = hour_visits.count()
        hourly_visits.append(count)
        
        # Calculate positivity (percentage of happy emotions)
        if count > 0:
            happy_count = hour_visits.filter(emotion='happy').count()
            positivity = (happy_count / count) * 100
        else:
            positivity = 0
            
        hourly_positivity.append(round(positivity, 1))

    # Debug info - you can remove this in production
    print(f"Emotion labels: {emotion_labels}")
    print(f"Emotion counts: {emotion_counts}")
    print(f"Hourly visits: {hourly_visits}")
    print(f"Hourly positivity: {hourly_positivity}")

    context = {
        'branch': branch,
        'visits': visits,
        'total_emotions': total_emotions,
        'emotion_dist': emotion_dist,
        'emotion_labels': json.dumps(emotion_labels),
        'emotion_counts': json.dumps(emotion_counts),
        'emotion_colors': json.dumps(emotion_colors),
        'hourly_labels': json.dumps(hourly_labels),
        'hourly_visits': json.dumps(hourly_visits),
        'hourly_positivity': json.dumps(hourly_positivity),
    }
    
    return render(request, 'monitor/branch_detail.html', context)

@login_required
def emotion_analytics(request):
    # Example: Use the same logic as dashboard for demo purposes
    user_pc_prefix = None
    if request.user.is_superuser:
        user_pc_prefix = request.GET.get('branch', None)
    else:
        user_pc_prefix = get_user_pc_prefix(request.user)

    # Date range for analytics
    time_range = request.GET.get('range', 'week')
    if time_range == 'day':
        days = 1
    elif time_range == 'month':
        days = 30
    else:
        days = 7

    end_date = timezone.now()
    start_date = end_date - timedelta(days=days-1)

    # Trend data for chart
    emotion_data = get_emotion_data(user_pc_prefix, start_date, end_date)
    chart_data = {
        "labels": list(emotion_data['trend_labels']),
        "datasets": emotion_data['trend_datasets'],
    }

    # Hourly data for chart
    hourly_data = get_hourly_data(user_pc_prefix, "today")
    hourly_labels = hourly_data['labels']
    hourly_total = [sum([hourly_data[e][i] for e in ['happy', 'neutral', 'sad', 'angry', 'surprise']]) for i in range(24)]

    # Distribution for doughnut chart
    dist_labels = list(emotion_data['emotion_counts'].keys())
    dist_data = list(emotion_data['emotion_counts'].values())
    emotion_colors = {
        'happy': '#FFD166',
        'sad': '#118AB2',
        'angry': '#EF476F',
        'neutral': '#8A8A8A',
        'surprise': '#8338EC',
        'none': '#6C757D'
    }
    dist_colors = [emotion_colors.get(e, '#6C757D') for e in dist_labels]

    context = {
        "page_title": "Emotion Analytics",
        "chart_data": chart_data,
        "hourly_labels": json.dumps(hourly_labels),
        "hourly_data": json.dumps(hourly_total),
        "dist_labels": json.dumps(dist_labels),
        "dist_data": json.dumps(dist_data),
        "dist_colors": json.dumps(dist_colors),
        "time_range": time_range,
    }
    return render(request, 'monitor/emotion_analytics.html', context)