from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q, Max, Min, F, ExpressionWrapper, FloatField
from django.db.models.functions import ExtractHour, TruncDate
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.utils.timezone import get_default_timezone, make_aware as django_make_aware
import csv
from collections import defaultdict
from .models import Visitor, VisitLog, Branch, UserProfile
from django.db.models import Count, Q
from django.shortcuts import render
from datetime import date, timedelta
from collections import defaultdict
from .models import VisitLog, Branch
            

def is_superadmin(user):
    return user.is_superuser

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        return render(request, 'monitor/login.html', {'error': 'Invalid credentials'})
    return render(request, 'monitor/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def make_aware(date_str, end_of_day=False):
    if date_str:
        try:
            naive_date = datetime.strptime(date_str, '%Y-%m-%d')
            if end_of_day:
                naive_date = naive_date.replace(hour=23, minute=59, second=59)
            return timezone.make_aware(naive_date)
        except ValueError:
            return None
    return None

def calculate_growth(new, old):
    if old == 0:
        return 100.0 if new > 0 else 0.0
    return round(((new - old) / old) * 100, 1)

def activity_level(count):
    if count > 100: return "High"
    if count > 50: return "Medium"
    return "Low"

def nav_items():
    return [
        {'url': 'dashboard', 'name': 'Dashboard', 'icon': 'speedometer2'},
        {'url': 'visitors', 'name': 'Visitors', 'icon': 'people-fill'},
        {'url': 'visit_history', 'name': 'Visit History', 'icon': 'clock-history'},
        {'url': 'emotion_analytics', 'name': 'Emotion Analytics', 'icon': 'bar-chart-line-fill'},
        {'url': 'reports', 'name': 'Reports', 'icon': 'file-earmark-text'},
        {'url': 'settings', 'name': 'Settings', 'icon': 'gear-fill'},
    ]

@login_required
def dashboard(request):
    user = request.user
    user_branch = user.branch if not user.is_superuser else None

    # Base queryset with branch filtering
    base_queryset = VisitLog.objects.all()
    if user_branch:
        base_queryset = base_queryset.filter(branch=user_branch)

    # Handle time range parameter
    time_range = request.GET.get('range', '14days')
    range_map = {
        'day': 1,
        'week': 7,
        'month': 30,
        '14days': 14
    }
    trend_days = range_map.get(time_range, 14)
    today = timezone.now().date()
    trend_start = today - timedelta(days=trend_days)

    emotions = ['happy', 'neutral', 'sad', 'angry', 'surprise']

    # Emotion distribution data
    emotion_counts = base_queryset.filter(
        timestamp__date__gte=trend_start
    ).values('emotion').annotate(count=Count('id'))
    emotion_data = {e['emotion']: e['count'] for e in emotion_counts}
    total_detections = sum(emotion_data.values())
    context_emotion_data = [emotion_data.get(e, 0) for e in emotions]

    # Top emotion
    if total_detections > 0:
        top_emotion_key = max(emotion_data, key=lambda k: emotion_data[k])
        top_emotion = {
            'emotion': top_emotion_key,
            'percentage': round((emotion_data[top_emotion_key] / total_detections) * 100, 1)
        }
    else:
        top_emotion = {'emotion': 'N/A', 'percentage': 0}

    # Negative emotions
    negative_count = emotion_data.get('angry', 0) + emotion_data.get('sad', 0)
    negative_percentage = round((negative_count / total_detections) * 100, 1) if total_detections else 0

    # Negative growth
    yesterday = today - timedelta(days=1)
    yesterday_neg = base_queryset.filter(
        timestamp__date=yesterday,
        emotion__in=['angry', 'sad']
    ).count()
    today_neg = base_queryset.filter(
        timestamp__date=today,
        emotion__in=['angry', 'sad']
    ).count()
    negative_growth = calculate_growth(today_neg, yesterday_neg)

    # Activity level and peak time
    today_count = base_queryset.filter(timestamp__date=today).count()
    activity_level_str = activity_level(today_count)
    hourly_entries = base_queryset.filter(
        timestamp__date=today
    ).annotate(hour=ExtractHour('timestamp')).values('hour').annotate(count=Count('id'))
    if hourly_entries:
        peak_hour = max(hourly_entries, key=lambda x: x['count'])['hour']
        peak_time = f"{peak_hour:02d}:00"
    else:
        peak_time = "N/A"

    # Trend data (efficient, all emotions in one query)
    trend_dates = [trend_start + timedelta(days=i) for i in range(trend_days + 1)]
    trend_labels = [d.strftime('%b %d') for d in trend_dates]
    trend_qs = base_queryset.filter(
        timestamp__date__gte=trend_start,
        timestamp__date__lte=today
    ).values('emotion', 'timestamp__date').annotate(count=Count('id'))
    trend_counts = {emotion: {d: 0 for d in trend_dates} for emotion in emotions}
    for entry in trend_qs:
        emotion = entry['emotion']
        date = entry['timestamp__date']
        if emotion in trend_counts and date in trend_counts[emotion]:
            trend_counts[emotion][date] = entry['count']
    color_map = {
        'happy': '#2ecc71',
        'neutral': '#f1c40f',
        'sad': '#3498db',
        'angry': '#e74c3c',
        'surprise': '#9b59b6'
    }
    trend_datasets = []
    for emotion in emotions:
        trend_datasets.append({
            'label': emotion.title(),
            'data': [trend_counts[emotion][d] for d in trend_dates],
            'backgroundColor': color_map.get(emotion, '#ccc'),
            'stack': 'stack'
        })

    # Hourly activity (today or yesterday)
    hourly_range = request.GET.get('hourly', 'today')
    if hourly_range == 'yesterday':
        hourly_date = today - timedelta(days=1)
    else:
        hourly_date = today
    hourly_qs = base_queryset.filter(timestamp__date=hourly_date).annotate(
        hour=ExtractHour('timestamp')
    ).values('hour', 'emotion').annotate(count=Count('id'))
    hourly_happy = [0] * 24
    hourly_neutral = [0] * 24
    hourly_sad = [0] * 24
    hourly_angry = [0] * 24
    hourly_surprise = [0] * 24
    for entry in hourly_qs:
        hour = entry['hour']
        emotion = entry['emotion']
        count = entry['count']
        if hour is not None:
            if emotion == 'happy':
                hourly_happy[hour] = count
            elif emotion == 'neutral':
                hourly_neutral[hour] = count
            elif emotion == 'sad':
                hourly_sad[hour] = count
            elif emotion == 'angry':
                hourly_angry[hour] = count
            elif emotion == 'surprise':
                hourly_surprise[hour] = count

    context = {
        'tab': 'dashboard',
        'total_visitors': Visitor.objects.filter(visitlog__in=base_queryset).distinct().count(),
        'total_detections': total_detections,
        'emotion_labels': [e.title() for e in emotions],
        'emotion_data': context_emotion_data,
        'trend_labels': trend_labels,
        'trend_datasets': trend_datasets,
        'hourly_labels': [f"{h:02d}:00" for h in range(24)],
        'hourly_happy': hourly_happy,
        'hourly_neutral': hourly_neutral,
        'hourly_sad': hourly_sad,
        'hourly_angry': hourly_angry,
        'hourly_surprise': hourly_surprise,
        'time_range': time_range,
        'trend_days': trend_days,
        'hourly_range': hourly_range,
        'branch_name': user_branch.name if user_branch else "All Branches",
        'top_emotion': top_emotion,
        'negative_percentage': negative_percentage,
        'negative_growth': negative_growth,
        'activity_level': activity_level_str,
        'peak_time': peak_time,
        'nav_items': nav_items()
    }
    return render(request, 'monitor/dashboard.html', context)

@login_required
def visitors_view(request):
    user_branch = request.user.branch
    base_qs = Visitor.objects.annotate(
        visit_count=Count('visitlog'),
        last_seen=Max('visitlog__timestamp')
    ).order_by('-last_seen')
    if user_branch:
        base_qs = base_qs.filter(visitlog__branch=user_branch).distinct()
    date_from = make_aware(request.GET.get('date_from'))
    date_to = make_aware(request.GET.get('date_to'), end_of_day=True)
    visitors = base_qs
    if date_from:
        visitors = visitors.filter(visitlog__timestamp__gte=date_from)
    if date_to:
        visitors = visitors.filter(visitlog__timestamp__lte=date_to)
    if emotion_filter := request.GET.get('emotion'):
        visitors = visitors.filter(visitlog__emotion=emotion_filter)
    if search_query := request.GET.get('search'):
        visitors = visitors.filter(Q(face_id__icontains=search_query))
    paginator = Paginator(visitors, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    emotion_counts_qs = VisitLog.objects.all()
    if user_branch:
        emotion_counts_qs = emotion_counts_qs.filter(branch=user_branch)
    emotion_counts = emotion_counts_qs.values('emotion').annotate(
        count=Count('emotion')
    ).order_by('-count')
    context = {
        'tab': 'visitors',
        'visitors': page_obj,
        'emotion_counts': emotion_counts,
        'selected_emotion': request.GET.get('emotion'),
        'date_from': request.GET.get('date_from'),
        'date_to': request.GET.get('date_to'),
        'search_query': request.GET.get('search'),
        'branch_name': user_branch.name if user_branch else "All Branches",
        'nav_items': nav_items()
    }
    return render(request, 'monitor/visitors.html', context)

@login_required
def visitor_detail(request, visitor_id):
    visitor = Visitor.objects.prefetch_related('visitlog_set').get(pk=visitor_id)
    emotion_dist = visitor.visitlog_set.values('emotion').annotate(
        count=Count('emotion')
    ).order_by('-count')
    visits = visitor.visitlog_set.order_by('-timestamp')
    context = {
        'tab': 'visitors',
        'visitor': visitor,
        'emotion_dist': emotion_dist,
        'visits': visits,
        'nav_items': nav_items()
    }
    return render(request, 'monitor/visitor_detail.html', context)

@login_required
def visit_history_view(request):
    # Start with base queryset
    visits = VisitLog.objects.select_related('visitor', 'branch').order_by('-timestamp')
    
    # Apply branch filter for non-superusers
    if not request.user.is_superuser and request.user.branch:
        visits = visits.filter(branch=request.user.branch)
    
    # Get filters from request
    emotion_filter = request.GET.get('emotion')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    face_id_filter = request.GET.get('face_id')
    
    # Apply filters
    if emotion_filter:
        visits = visits.filter(emotion=emotion_filter)
    if date_from:
        visits = visits.filter(timestamp__date__gte=date_from)
    if date_to:
        next_day = (datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        visits = visits.filter(timestamp__date__lt=next_day)
    if face_id_filter:
        visits = visits.filter(visitor__face_id__icontains=face_id_filter)
    
    # Handle CSV export
    if 'export' in request.GET:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="visit_history.csv"'
        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Face ID', 'Emotion', 'Branch'])
        for visit in visits:
            writer.writerow([
                visit.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                visit.visitor.face_id if visit.visitor else 'Unknown',
                visit.emotion,
                visit.branch.name if visit.branch else ''
            ])
        return response
    
    # Group visits by day and visitor
    grouped_visits = visits.annotate(
        visit_date=TruncDate('timestamp')
    ).values(
        'visitor_id', 
        'visit_date',
        'branch__name'
    ).annotate(
        first_visit=Min('timestamp'),
        last_visit=Max('timestamp'),
        visit_count=Count('id'),
        face_id=F('visitor__face_id')  # Get face_id directly
    ).order_by('-visit_date')
    
    # Pagination
    paginator = Paginator(grouped_visits, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'tab': 'visit_history',
        'visits': page_obj,
        'selected_emotion': emotion_filter,
        'date_from': date_from,
        'date_to': date_to,
        'face_id': face_id_filter,
        'nav_items': nav_items()
    }
    return render(request, 'monitor/visit_history.html', context)

@login_required
def emotion_analytics_view(request):
    # Determine time range
    time_range = request.GET.get('range', 'week')
    today = date.today()
    
    # Get user's branch if not superuser
    user_branch = None
    if not request.user.is_superuser:
        user_branch = request.user.branch
    
    # Set date ranges
    if time_range == 'day':
        start_date = today
        end_date = today + timedelta(days=1)
    elif time_range == 'week':
        start_date = today - timedelta(days=7)
        end_date = today + timedelta(days=1)
    else:  # month
        start_date = today - timedelta(days=30)
        end_date = today + timedelta(days=1)

    # Base queryset for trend data
    trend_queryset = VisitLog.objects.filter(
        timestamp__date__range=(start_date, end_date)
    )
    
    # Filter by branch if not superuser
    if user_branch:
        trend_queryset = trend_queryset.filter(branch=user_branch)
    
    # Get trend data
    trend_data = trend_queryset.values('emotion', 'timestamp__date').annotate(
        count=Count('id')
    ).order_by('timestamp__date')

    # Prepare labels and emotion data
    labels = set()
    emotion_data = defaultdict(dict)
    for entry in trend_data:
        date_str = entry['timestamp__date'].strftime('%b %d')
        labels.add(date_str)
        emotion_data[entry['emotion']][date_str] = entry['count']
    sorted_labels = sorted(labels)

    # Prepare chart datasets
    datasets = []
    colors = {
        'happy': '#2ecc71',
        'neutral': '#95a5a6',
        'sad': '#e74c3c',
        'angry': '#f39c12',
        'surprise': '#3498db'
    }
    
    # Ensure all emotions are included
    for emotion in colors:
        datasets.append({
            'label': emotion.title(),
            'data': [emotion_data[emotion].get(label, 0) for label in sorted_labels],
            'borderColor': colors[emotion],
            'backgroundColor': f"{colors[emotion]}33",
        })

    # Prepare hourly data
    hourly_labels = [f"{h}:00" for h in range(8, 18)]
    hourly_data = []
    hourly_queryset = VisitLog.objects.filter(timestamp__date=today)
    if user_branch:
        hourly_queryset = hourly_queryset.filter(branch=user_branch)
    
    for hour in range(8, 18):
        count = hourly_queryset.filter(timestamp__hour=hour).count()
        hourly_data.append(count)

    # Prepare distribution data
    dist_labels = ['Happy', 'Neutral', 'Sad', 'Angry', 'Surprise']
    dist_data = []
    dist_queryset = VisitLog.objects.filter(
        timestamp__date__gte=today - timedelta(days=7)
    )
    if user_branch:
        dist_queryset = dist_queryset.filter(branch=user_branch)
    
    for emotion in ['happy', 'neutral', 'sad', 'angry', 'surprise']:
        count = dist_queryset.filter(emotion=emotion).count()
        dist_data.append(count)

    # Branch comparison - only for superusers
    branch_comparison = None
    if request.user.is_superuser:
        branch_comparison = Branch.objects.annotate(
            total_visits=Count('visit_logs'),
            happy=Count('visit_logs', filter=Q(visit_logs__emotion='happy')),
            neutral=Count('visit_logs', filter=Q(visit_logs__emotion='neutral')),
            negative=Count('visit_logs', filter=Q(visit_logs__emotion__in=['angry', 'sad']))
        ).order_by('-total_visits')
        
        # Convert counts to percentages
        for branch in branch_comparison:
            total = branch.total_visits or 1
            branch.happy = round((branch.happy / total) * 100, 1)
            branch.neutral = round((branch.neutral / total) * 100, 1)
            branch.negative = round((branch.negative / total) * 100, 1)

    context = {
        'tab': 'emotion_analytics',
        'chart_data': {
            'labels': sorted_labels,
            'datasets': datasets
        },
        'hourly_labels': hourly_labels,
        'hourly_data': hourly_data,
        'dist_labels': dist_labels,
        'dist_data': dist_data,
        'time_range': time_range,
        'branch_comparison': branch_comparison,
        'nav_items': nav_items() if callable(nav_items) else []
    }
    return render(request, 'monitor/emotion_analytics.html', context)

@login_required
@user_passes_test(is_superadmin)
def branch_overview(request):
    # Get time range from URL parameter
    time_range = request.GET.get('range', 'week')  # Default to week
    
    # Get current time in the server's timezone
    now = timezone.localtime(timezone.now())
    end_date = now.date()
    
    # Calculate date range based on selection
    if time_range == 'day':
        days = [end_date]  # Today only
    elif time_range == 'week':
        days = [end_date - timedelta(days=i) for i in range(6, -1, -1)]  # Last 7 days
    else:  # month
        days = [end_date - timedelta(days=i) for i in range(29, -1, -1)]  # Last 30 days
    
    iso_days = [d.strftime('%Y-%m-%d') for d in days]  # ISO format for Chart.js
    formatted_days = [d.strftime('%b %d') for d in days]  # Formatted for table display

    # Annotate branches with performance metrics
    branches = Branch.objects.annotate(
        total_visits=Count('visit_logs'),
        happy=Count('visit_logs', filter=Q(visit_logs__emotion='happy')),
        neutral=Count('visit_logs', filter=Q(visit_logs__emotion='neutral')),
        sad=Count('visit_logs', filter=Q(visit_logs__emotion='sad')),
        angry=Count('visit_logs', filter=Q(visit_logs__emotion='angry')),
        surprise=Count('visit_logs', filter=Q(visit_logs__emotion='surprise')),
        visitor_count=Count('visit_logs__visitor', distinct=True),
        positivity_score=ExpressionWrapper(
            F('happy') * 1.0 / F('total_visits'),
            output_field=FloatField()
        )
    ).order_by('-total_visits')
    
    # Prepare chart datasets
    chart_datasets = []
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
    
    # Get server timezone for accurate date filtering
    tz = get_default_timezone()
    from datetime import datetime, time

    for i, branch in enumerate(branches):
        # Calculate daily counts for this branch
        daily_counts = []
        for day in days:
            # Create datetime range for the day
                       
            start_datetime = django_make_aware(datetime.combine(day, time.min), timezone=tz)
            end_datetime = start_datetime + timedelta(days=1)
            
            count = branch.visit_logs.filter(
                timestamp__gte=start_datetime,
                timestamp__lt=end_datetime
            ).count()
            daily_counts.append(count)
        
        # Format data for Chart.js
        data_points = [{"x": iso_days[j], "y": daily_counts[j]} for j in range(len(days))]
        
        chart_datasets.append({
            "label": branch.name,
            "data": data_points,
            "borderColor": colors[i % len(colors)],
            "backgroundColor": colors[i % len(colors)] + '33',  # Add transparency
            "tension": 0.3,
            "fill": False
        })

        # Determine top emotion and trends for table display
        emotions = {
            'happy': branch.happy,
            'neutral': branch.neutral,
            'sad': branch.sad,
            'angry': branch.angry,
            'surprise': branch.surprise
        }
        branch.top_emotion = max(emotions, key=emotions.get) if branch.total_visits > 0 else 'neutral'
        branch.positivity_percent = int((branch.positivity_score or 0) * 100)
        branch.trend_visits = daily_counts
        branch.trend_days = formatted_days

    # Add debug data to context
    debug_info = {
        'time_range': time_range,
        'days': [d.strftime('%Y-%m-%d') for d in days],
        'branch_count': len(branches),
        'has_data': any(daily_counts for branch in branches)
    }

    context = {
        'tab': 'branches',
        'branches': branches,
        'chart_datasets': chart_datasets,
        'time_range': time_range,
        'debug_info': debug_info,  # For debugging
        'nav_items': nav_items()
    }
    return render(request, 'monitor/branch_overview.html', context)

@login_required
def reports_view(request):
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        format = request.POST.get('format')
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        # Implement report generation logic here
        return HttpResponse("Report generation would be implemented here")
    context = {
        'tab': 'reports',
        'nav_items': nav_items()
    }
    return render(request, 'monitor/reports.html', context)

@login_required
@user_passes_test(is_superadmin)
def branch_detail(request, branch_id):
    branch = get_object_or_404(Branch, pk=branch_id)
    visits = VisitLog.objects.filter(branch=branch).select_related('visitor')
    emotion_dist = list(visits.values('emotion').annotate(count=Count('emotion')).order_by('-count'))
    total_emotions = sum(e['count'] for e in emotion_dist)
    emotion_labels = [e['emotion'].title() for e in emotion_dist]
    emotion_counts = [e['count'] for e in emotion_dist]
    hourly_activity = list(
        visits.annotate(hour=ExtractHour('timestamp'))
        .values('hour')
        .annotate(count=Count('id'))
        .order_by('hour')
    )
    hourly_labels = [f"{h['hour']}:00" for h in hourly_activity]
    hourly_visits = [h['count'] for h in hourly_activity]
    hourly_positivity = []
    for h in hourly_activity:
        happy_count = visits.filter(
            emotion='happy',
            timestamp__hour=h['hour']
        ).count()
        positivity = int((happy_count / h['count']) * 100) if h['count'] > 0 else 0
        hourly_positivity.append(positivity)
    recent_visits = visits.order_by('-timestamp')[:10]
    context = {
        'branch': branch,
        'emotion_dist': emotion_dist,
        'emotion_labels': emotion_labels,
        'emotion_counts': emotion_counts,
        'hourly_activity': hourly_activity,
        'hourly_labels': hourly_labels,
        'hourly_visits': hourly_visits,
        'hourly_positivity': hourly_positivity,
        'total_emotions': total_emotions,
        'visits': recent_visits,
        'nav_items': nav_items()
    }
    return render(request, 'monitor/branch_detail.html', context)

@login_required
def settings_view(request):
    user = request.user
    user_profile, created = UserProfile.objects.get_or_create(user=user)
    if request.method == 'POST':
        user_profile.dark_mode = request.POST.get('dark_mode') == 'on'
        user_profile.notify_weekly = request.POST.get('notify_weekly') == 'on'
        user_profile.notify_negative = request.POST.get('notify_negative') == 'on'
        user_profile.save()
        return redirect('settings')
    context = {
        'tab': 'settings',
        'nav_items': nav_items()
    }
    return render(request, 'monitor/settings.html', context)