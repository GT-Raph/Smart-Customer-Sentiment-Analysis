# monitor/urls.py
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.login_view, name='login'),
    # path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),  # now our custom view
    path('dashboard/', views.dashboard, name='dashboard'),
    path('branches/', views.branch_overview, name='branch_overview'),
    path('reports/', views.reports, name='reports'),
    path('settings/', views.settings, name='settings'),
    path('branch/<int:branch_id>/', views.branch_detail, name='branch_detail'),
    path('emotion-analytics/', views.emotion_analytics, name='emotion_analytics'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
