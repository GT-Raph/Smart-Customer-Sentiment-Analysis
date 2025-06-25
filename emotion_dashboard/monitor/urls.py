from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
import os

urlpatterns = [
    # Authentication
    path('', views.login_view, name='root_login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    # path('hourly-activity/', views.hourly_activity_view, name='hourly_activity'),
    
    # Visitors
    path('visitors/', views.visitors_view, name='visitors'),
    path('visitors/<int:visitor_id>/', views.visitor_detail, name='visitor_detail'),
    path('face_images/<str:filename>/', views.serve_face_image, name='face_image'),
    
    # Visit History
    path('visits/', views.visit_history_view, name='visit_history'),
    
    # Analytics
    path('analytics/', views.emotion_analytics_view, name='emotion_analytics'),
    
    # Branch Management (Super Admin only)
    path('branches/', views.branch_overview, name='branch_overview'),
    path('branches/<int:branch_id>/', views.branch_detail, name='branch_detail'),
    
    # Reports
    path('reports/', views.reports_view, name='reports'),
    
    # Settings
    path('settings/', views.settings_view, name='settings'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, 
        document_root=os.path.join(settings.BASE_DIR, 'emotion_detection_system', 'known_faces')
    )