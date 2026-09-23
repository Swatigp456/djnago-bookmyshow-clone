from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from movies import views

urlpatterns = [
    # ============================================
    # ADMIN DASHBOARD & ANALYTICS URLs (MUST COME FIRST)
    # ============================================
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/analytics/revenue/', views.analytics_revenue, name='analytics_revenue'),
    path('admin/analytics/occupancy/', views.analytics_occupancy, name='analytics_occupancy'),
    path('admin/analytics/top-movies/', views.analytics_top_movies, name='analytics_top_movies'),
    path('admin/analytics/peak-hours/', views.analytics_peak_hours, name='analytics_peak_hours'),
    path('admin/analytics/cancellations/', views.analytics_cancellations, name='analytics_cancellations'),
    path('admin/analytics/users/', views.analytics_users, name='analytics_users'),
    path('admin/export-csv/', views.export_csv_report, name='export_csv_report'),
    
    # ============================================
    # DEFAULT DJANGO ADMIN (MUST COME AFTER CUSTOM URLs)
    # ============================================
    path('admin/', admin.site.urls),
    
    # ============================================
    # OTHER APP URLs
    # ============================================
    path('', include('users.urls')),
    path('movies/', include('movies.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)