from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Movie, Theater, Seat, Booking, Genre, Language, Cast, 
    Review, ReviewReport, MovieCast, Screen, Show, ShowBooking,
    Payment, AnalyticsEvent, DailyReport  # ✅ ADDED AnalyticsEvent and DailyReport
)
from django.utils import timezone

# ============================================
# YOUR EXISTING ADMIN CLASSES - KEPT EXACTLY AS IS
# ============================================

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['name', 'rating', 'cast', 'description']


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ['name', 'movie', 'time']


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['theater', 'seat_number', 'is_booked']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'seat', 'movie', 'theater', 'booked_at']


# ============================================
# NEW ADMIN CLASSES ADDED FOR TASK FEATURES
# ============================================

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']
    list_filter = ['created_at']


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']


@admin.register(Cast)
class CastAdmin(admin.ModelAdmin):
    list_display = ['name', 'gender', 'nationality', 'display_photo']
    list_filter = ['gender', 'nationality']
    search_fields = ['name', 'bio']
    
    def display_photo(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.photo.url)
        return "No Photo"
    display_photo.short_description = 'Photo'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['movie', 'user', 'rating', 'is_approved', 'is_verified', 'is_reported', 'created_at']
    list_filter = ['is_approved', 'is_verified', 'is_reported', 'rating']
    search_fields = ['movie__name', 'user__username', 'review_text']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['approve_reviews', 'unapprove_reviews']
    
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f"{queryset.count()} reviews approved successfully.")
    approve_reviews.short_description = "Approve selected reviews"
    
    def unapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, f"{queryset.count()} reviews unapproved.")
    unapprove_reviews.short_description = "Unapprove selected reviews"


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ['review', 'reported_by', 'reason', 'is_resolved', 'created_at']
    list_filter = ['is_resolved', 'reason']
    search_fields = ['review__review_text', 'reported_by__username']
    readonly_fields = ['created_at']
    actions = ['resolve_reports']
    
    def resolve_reports(self, request, queryset):
        queryset.update(is_resolved=True, resolved_at=timezone.now(), resolved_by=request.user)
        self.message_user(request, f"{queryset.count()} reports resolved.")
    resolve_reports.short_description = "Resolve selected reports"


@admin.register(MovieCast)
class MovieCastAdmin(admin.ModelAdmin):
    list_display = ['movie', 'cast', 'role', 'character_name', 'is_lead', 'order']
    list_filter = ['role', 'is_lead']
    search_fields = ['movie__name', 'cast__name', 'character_name']
    ordering = ['movie', 'order']


@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ['theater', 'screen_number', 'capacity', 'is_active']
    list_filter = ['is_active', 'theater']
    search_fields = ['theater__name', 'screen_number']
    ordering = ['theater', 'screen_number']


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ['movie', 'screen', 'show_date', 'show_time', 'price', 'status', 'is_active']
    list_filter = ['status', 'is_active', 'show_date', 'movie']
    search_fields = ['movie__name', 'screen__theater__name']
    date_hierarchy = 'show_date'
    ordering = ['-show_date', 'show_time']
    
    fieldsets = (
        ('Movie & Screen', {
            'fields': ('movie', 'screen')
        }),
        ('Schedule', {
            'fields': ('show_date', 'show_time')
        }),
        ('Pricing & Status', {
            'fields': ('price', 'status', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ['created_at']


@admin.register(ShowBooking)
class ShowBookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'show', 'seats', 'total_price', 'status', 'booking_date']
    list_filter = ['status', 'booking_date']
    search_fields = ['user__username', 'show__movie__name']
    date_hierarchy = 'booking_date'
    ordering = ['-booking_date']
    
    fieldsets = (
        ('User & Show', {
            'fields': ('user', 'show')
        }),
        ('Booking Details', {
            'fields': ('seats', 'total_price')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Metadata', {
            'fields': ('booking_date',),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ['booking_date']
    
    actions = ['confirm_bookings', 'cancel_bookings']
    
    def confirm_bookings(self, request, queryset):
        queryset.update(status='CONFIRMED')
        self.message_user(request, f"{queryset.count()} bookings confirmed.")
    confirm_bookings.short_description = "Confirm selected bookings"
    
    def cancel_bookings(self, request, queryset):
        queryset.update(status='CANCELLED')
        self.message_user(request, f"{queryset.count()} bookings cancelled.")
    cancel_bookings.short_description = "Cancel selected bookings"


# ============================================
# PAYMENT ADMIN
# ============================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'booking', 'amount', 'payment_status', 'payment_method', 'created_at']
    list_filter = ['payment_status', 'payment_method', 'created_at']
    search_fields = ['user__username', 'razorpay_order_id', 'razorpay_payment_id']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['mark_success', 'mark_failed', 'mark_refunded']
    
    def mark_success(self, request, queryset):
        for payment in queryset:
            payment.payment_status = 'SUCCESS'
            payment.save()
        self.message_user(request, f"{queryset.count()} payments marked as SUCCESS.")
    mark_success.short_description = "Mark selected payments as SUCCESS"
    
    def mark_failed(self, request, queryset):
        for payment in queryset:
            payment.payment_status = 'FAILED'
            payment.save()
        self.message_user(request, f"{queryset.count()} payments marked as FAILED.")
    mark_failed.short_description = "Mark selected payments as FAILED"
    
    def mark_refunded(self, request, queryset):
        for payment in queryset:
            payment.payment_status = 'REFUNDED'
            payment.save()
        self.message_user(request, f"{queryset.count()} payments marked as REFUNDED.")
    mark_refunded.short_description = "Mark selected payments as REFUNDED"


# ============================================
# ANALYTICS ADMIN (ADDED FOR TASK 4)
# ============================================

@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'user', 'movie', 'theater', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['user__username', 'movie__name', 'session_id']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False  # Events are created automatically


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_bookings', 'total_revenue', 'total_cancellations', 'occupancy_rate']
    list_filter = ['date']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    def has_add_permission(self, request):
        return False  # Reports are generated automatically