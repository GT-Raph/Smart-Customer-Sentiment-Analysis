from django.http import HttpResponse
from django.db.models import Count
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .models import CapturedSnapshot
from datetime import timedelta, datetime
import json
from django.core.exceptions import PermissionDenied
from django.contrib.auth import authenticate, login


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
    # Get the user's PC name prefix from their profile or settings
    user_pc_prefix = get_user_pc_prefix(request.user)
    
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
    total_visitors_today = CapturedSnapshot.objects.filter(
        timestamp__date=today
    ).values("visitor__face_id").distinct().count()


    # ✅ Top emotion today
    emotion_counts_today = (
        CapturedSnapshot.objects.filter(timestamp__date=today)
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
    
    # Calculate negative emotions for today
    negative_emotions_today = sum(
        e["total"] for e in emotion_counts_today 
        if e["emotion"] in ['sad', 'angry']
    )
    total_detections_today = sum(e["total"] for e in emotion_counts_today)
    negative_percentage_today = round((negative_emotions_today / total_detections_today * 100), 1) if total_detections_today > 0 else 0
    
    context = {
        'branch_name': user_pc_prefix or 'All Branches',
        'total_visitors': total_visitors_today,
        'visitor_growth': calculate_growth(user_pc_prefix),
        'top_emotion': top_emotion_today,
        'negative_percentage': negative_percentage_today,
        'negative_growth': calculate_negative_growth(user_pc_prefix),
        'activity_level': get_activity_level(total_visitors_today),
        'peak_time': get_peak_time(hourly_data),
        'total_detections': total_detections_today,
        'emotion_labels': json.dumps(list(emotion_data['emotion_counts'].keys())),
        'emotion_data': json.dumps(list(emotion_data['emotion_counts'].values())),
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
    
    # Calculate negative emotions percentage
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
    
    # Get today's negative emotions
    query_today = CapturedSnapshot.objects.filter(
        timestamp__date=today,
        emotion__in=['sad', 'angry']
    )
    if pc_prefix:
        query_today = query_today.filter(pc_name__startswith=pc_prefix)
    today_negative = query_today.count()
    
    # Get yesterday's negative emotions
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
    context = {
        'page_title': 'Branch Overview',
        # Add your branch data here
    }
    return render(request, 'monitor/branch_overview.html', context)

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
    # You can fetch branch details and pass to the template as needed
    from .models import Branch
    branch = Branch.objects.get(pk=branch_id)
    context = {
        'branch': branch,
        'page_title': f'Branch Details: {branch.name}',
    }
    return render(request, 'monitor/branch_detail.html', context)

@login_required
def emotion_analytics(request):
    context = {
        'page_title': 'Emotion Analytics',
        # Add your analytics data here
    }
    return render(request, 'monitor/emotion_analytics.html', context)