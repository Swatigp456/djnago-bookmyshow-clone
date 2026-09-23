# movies/analytics_utils.py
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek, TruncDay
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import csv
from io import StringIO
from .models import ShowBooking, Payment, Movie, Theater, Screen, User, AnalyticsEvent, DailyReport


class AnalyticsService:
    """Service for generating analytics data"""
    
    @staticmethod
    def get_revenue_data(start_date=None, end_date=None, period='daily'):
        """
        Get revenue data for the given period
        """
        bookings = ShowBooking.objects.filter(status='CONFIRMED')
        
        if start_date:
            bookings = bookings.filter(booking_date__date__gte=start_date)
        if end_date:
            bookings = bookings.filter(booking_date__date__lte=end_date)
        
        if period == 'daily':
            data = bookings.annotate(
                date=TruncDate('booking_date')
            ).values('date').annotate(
                revenue=Sum('total_price'),
                count=Count('id')
            ).order_by('date')
        elif period == 'weekly':
            data = bookings.annotate(
                week=TruncWeek('booking_date')
            ).values('week').annotate(
                revenue=Sum('total_price'),
                count=Count('id')
            ).order_by('week')
        elif period == 'monthly':
            data = bookings.annotate(
                month=TruncMonth('booking_date')
            ).values('month').annotate(
                revenue=Sum('total_price'),
                count=Count('id')
            ).order_by('month')
        else:  # yearly
            data = bookings.annotate(
                year=TruncMonth('booking_date')
            ).values('year').annotate(
                revenue=Sum('total_price'),
                count=Count('id')
            ).order_by('year')
        
        return list(data)
    
    @staticmethod
    def get_booking_trends(start_date=None, end_date=None):
        """
        Get booking trends including daily, weekly, monthly aggregates
        """
        bookings = ShowBooking.objects.filter(status='CONFIRMED')
        
        if start_date:
            bookings = bookings.filter(booking_date__date__gte=start_date)
        if end_date:
            bookings = bookings.filter(booking_date__date__lte=end_date)
        
        # Daily trends
        daily_trends = bookings.annotate(
            date=TruncDate('booking_date')
        ).values('date').annotate(
            bookings=Count('id'),
            revenue=Sum('total_price')
        ).order_by('date')
        
        # Weekly trends
        weekly_trends = bookings.annotate(
            week=TruncWeek('booking_date')
        ).values('week').annotate(
            bookings=Count('id'),
            revenue=Sum('total_price')
        ).order_by('week')
        
        # Monthly trends
        monthly_trends = bookings.annotate(
            month=TruncMonth('booking_date')
        ).values('month').annotate(
            bookings=Count('id'),
            revenue=Sum('total_price')
        ).order_by('month')
        
        return {
            'daily': list(daily_trends),
            'weekly': list(weekly_trends),
            'monthly': list(monthly_trends)
        }
    
    @staticmethod
    def get_theater_occupancy(start_date=None, end_date=None):
        """
        Get occupancy percentage for each theater
        """
        theaters = Theater.objects.all()
        occupancy_data = []
        
        for theater in theaters:
            total_capacity = Screen.objects.filter(
                theater=theater,
                is_active=True
            ).aggregate(total=Sum('capacity'))['total'] or 0
            
            if total_capacity == 0:
                continue
            
            # Get bookings for this theater
            bookings = ShowBooking.objects.filter(
                show__screen__theater=theater,
                status='CONFIRMED'
            )
            
            if start_date:
                bookings = bookings.filter(booking_date__date__gte=start_date)
            if end_date:
                bookings = bookings.filter(booking_date__date__lte=end_date)
            
            total_bookings = bookings.count()
            
            occupancy_rate = (total_bookings / total_capacity) * 100 if total_capacity > 0 else 0
            
            occupancy_data.append({
                'theater_id': theater.id,
                'theater_name': theater.name,
                'total_capacity': total_capacity,
                'total_bookings': total_bookings,
                'occupancy_rate': round(occupancy_rate, 2)
            })
        
        return sorted(occupancy_data, key=lambda x: x['occupancy_rate'], reverse=True)
    
    @staticmethod
    def get_top_movies(start_date=None, end_date=None, limit=10):
        """
        Get most booked movies
        """
        bookings = ShowBooking.objects.filter(status='CONFIRMED')
        
        if start_date:
            bookings = bookings.filter(booking_date__date__gte=start_date)
        if end_date:
            bookings = bookings.filter(booking_date__date__lte=end_date)
        
        top_movies = bookings.values(
            'show__movie__id',
            'show__movie__name'
        ).annotate(
            total_bookings=Count('id'),
            total_revenue=Sum('total_price'),
            avg_rating=Avg('show__movie__rating')
        ).order_by('-total_bookings')[:limit]
        
        return list(top_movies)
    
    @staticmethod
    def get_top_theaters(start_date=None, end_date=None, limit=10):
        """
        Get top-performing theaters
        """
        bookings = ShowBooking.objects.filter(status='CONFIRMED')
        
        if start_date:
            bookings = bookings.filter(booking_date__date__gte=start_date)
        if end_date:
            bookings = bookings.filter(booking_date__date__lte=end_date)
        
        top_theaters = bookings.values(
            'show__screen__theater__id',
            'show__screen__theater__name'
        ).annotate(
            total_bookings=Count('id'),
            total_revenue=Sum('total_price')
        ).order_by('-total_revenue')[:limit]
        
        return list(top_theaters)
    
    @staticmethod
    def get_peak_hours(start_date=None, end_date=None):
        """
        Get peak booking hours
        """
        bookings = ShowBooking.objects.filter(status='CONFIRMED')
        
        if start_date:
            bookings = bookings.filter(booking_date__date__gte=start_date)
        if end_date:
            bookings = bookings.filter(booking_date__date__lte=end_date)
        
        from django.db.models.functions import ExtractHour
        
        peak_hours = bookings.annotate(
            hour=ExtractHour('booking_date')
        ).values('hour').annotate(
            bookings=Count('id')
        ).order_by('-bookings')
        
        return list(peak_hours)
    
    @staticmethod
    def get_cancellation_stats(start_date=None, end_date=None):
        """
        Get cancellation and refund statistics
        """
        bookings = ShowBooking.objects.filter(
            status__in=['CANCELLED', 'REFUNDED']
        )
        
        if start_date:
            bookings = bookings.filter(booking_date__date__gte=start_date)
        if end_date:
            bookings = bookings.filter(booking_date__date__lte=end_date)
        
        total_cancellations = bookings.filter(status='CANCELLED').count()
        total_refunds = bookings.filter(status='REFUNDED').count()
        refund_amount = Payment.objects.filter(
            payment_status='REFUNDED'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return {
            'total_cancellations': total_cancellations,
            'total_refunds': total_refunds,
            'refund_amount': float(refund_amount)
        }
    
    @staticmethod
    def get_user_growth(start_date=None, end_date=None):
        """
        Get user growth reports
        """
        users = User.objects.all()
        
        if start_date:
            users = users.filter(date_joined__date__gte=start_date)
        if end_date:
            users = users.filter(date_joined__date__lte=end_date)
        
        daily_growth = users.annotate(
            date=TruncDate('date_joined')
        ).values('date').annotate(
            new_users=Count('id')
        ).order_by('date')
        
        total_users = User.objects.count()
        
        return {
            'total_users': total_users,
            'daily_growth': list(daily_growth)
        }
    
    @staticmethod
    def get_dashboard_summary():
        """
        Get overall dashboard summary
        """
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)
        
        # Total revenue
        total_revenue = Payment.objects.filter(
            payment_status='SUCCESS'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Daily revenue
        daily_revenue = Payment.objects.filter(
            payment_status='SUCCESS',
            paid_at__date=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Weekly revenue
        weekly_revenue = Payment.objects.filter(
            payment_status='SUCCESS',
            paid_at__date__gte=start_of_week
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Monthly revenue
        monthly_revenue = Payment.objects.filter(
            payment_status='SUCCESS',
            paid_at__date__gte=start_of_month
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Total bookings
        total_bookings = ShowBooking.objects.filter(status='CONFIRMED').count()
        
        # Active users
        active_users = User.objects.filter(is_active=True).count()
        
        # Today's bookings
        today_bookings = ShowBooking.objects.filter(
            status='CONFIRMED',
            booking_date__date=today
        ).count()
        
        # Overall occupancy
        total_capacity = Screen.objects.filter(is_active=True).aggregate(
            total=Sum('capacity')
        )['total'] or 0
        
        total_occupied = ShowBooking.objects.filter(
            status='CONFIRMED'
        ).count()
        
        overall_occupancy = (total_occupied / total_capacity * 100) if total_capacity > 0 else 0
        
        return {
            'total_revenue': float(total_revenue),
            'daily_revenue': float(daily_revenue),
            'weekly_revenue': float(weekly_revenue),
            'monthly_revenue': float(monthly_revenue),
            'total_bookings': total_bookings,
            'active_users': active_users,
            'today_bookings': today_bookings,
            'overall_occupancy': round(overall_occupancy, 2)
        }
    
    @staticmethod
    def generate_csv_report(data, filename):
        """
        Generate CSV report from data
        """
        output = StringIO()
        writer = csv.writer(output)
        
        if not data:
            return output.getvalue()
        
        # Get headers from first item
        headers = list(data[0].keys())
        writer.writerow(headers)
        
        # Write data rows
        for row in data:
            writer.writerow([row.get(header, '') for header in headers])
        
        return output.getvalue()