from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Avg, Count
import re


# ============================================
# YOUR EXISTING MODELS - KEPT EXACTLY AS IS
# ============================================

class Movie(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to="movies/")
    rating = models.DecimalField(max_digits=3, decimal_places=1)
    cast = models.TextField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    theater = models.CharField(max_length=255, blank=True, null=True)
    show_timings = models.JSONField(default=list, blank=True)  # Store show timings
    
    
    # ========== ADDED FIELDS FOR TRENDING, RECENT, AND MORE ==========
    is_trending = models.BooleanField(default=False)
    is_recent = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    release_date = models.DateField(blank=True, null=True)
    duration = models.PositiveIntegerField(blank=True, null=True, help_text="Duration in minutes")
    director = models.CharField(max_length=200, blank=True)
    producer = models.CharField(max_length=200, blank=True)
    trailer_url = models.URLField(blank=True, null=True, help_text="YouTube URL for trailer")
    trailer_embed_id = models.CharField(max_length=50, blank=True, null=True, help_text="YouTube video ID for embedding")
    additional_posters = models.ImageField(upload_to='movie_posters/extra/', blank=True, null=True)
    budget = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    box_office = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    certification = models.CharField(max_length=2, blank=True, null=True, choices=[
        ('U', 'U - Universal'),
        ('UA', 'UA - Parental Guidance'),
        ('A', 'A - Adult Only'),
        ('S', 'S - Restricted'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Many-to-many relationships (commented out - uncomment if needed)
    genres = models.CharField(max_length=255, blank=True, null=True, help_text="Comma separated genres (e.g., Action, Drama)")
    language = models.CharField(max_length=100, blank=True, null=True, help_text="Movie language (e.g., English, Hindi)")
    def __str__(self):
        return self.name
    
    def get_average_rating(self):
        """Calculate average rating for the movie"""
        from django.db.models import Avg
        avg = self.reviews.filter(is_approved=True).aggregate(Avg('rating'))
        return avg['rating__avg'] or 0
    
    def get_rating_count(self):
        """Get total number of ratings"""
        return self.reviews.filter(is_approved=True).count()
    
    def get_recent_reviews(self, limit=5):
        """Get recent approved reviews"""
        return self.reviews.filter(is_approved=True).order_by('-created_at')[:limit]
    
    def get_similar_movies(self, limit=4):
        """Get similar movies based on genres and languages"""
        # Simple version - just get other active movies
        return Movie.objects.filter(is_active=True).exclude(id=self.id)[:limit]
    
    def get_upcoming_shows(self):
        """Get upcoming shows for this movie"""
        from django.utils import timezone
        return self.shows.filter(
            show_date__gte=timezone.now().date(),
            is_active=True
        ).order_by('show_date', 'show_time')
    
    def get_youtube_id(self, url):
        """Extract YouTube video ID from URL"""
        import re
        patterns = [
            r'youtube\.com/watch\?v=([^&]+)',
            r'youtu\.be/([^?]+)',
            r'youtube\.com/embed/([^?]+)',
            r'youtube\.com/v/([^?]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    def get_view_count(self):
        """Get number of times this movie was viewed"""
        return AnalyticsEvent.objects.filter(
            movie=self,
            event_type='VIEW'
        ).count()
    
    def get_booking_count(self):
        """Get number of bookings for this movie"""
        return ShowBooking.objects.filter(
            show__movie=self,
            status='CONFIRMED'
        ).count()
    
    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['release_date']),
            models.Index(fields=['rating']),
            models.Index(fields=['city']),
            models.Index(fields=['theater']),
        ]
   


class Theater(models.Model):
    name = models.CharField(max_length=255)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='theaters')
    time = models.DateTimeField()

    def __str__(self):
        return f'{self.name} - {self.movie.name} at {self.time}'


class Seat(models.Model):
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='seats')
    # FIXED: Added screen field to create relationship between Seat and Screen
    screen = models.ForeignKey('Screen', on_delete=models.CASCADE, related_name='seats', null=True, blank=True)
    seat_number = models.CharField(max_length=10)
    is_booked = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.seat_number} in {self.theater.name}'
    
    def get_current_status(self, show=None):
        """Get current seat status for a specific show"""
        from django.utils import timezone
        
        if not show:
            return 'AVAILABLE'
        
        # Check if booked
        if show.bookings.filter(seat=self, status='CONFIRMED').exists():
            return 'BOOKED'
        
        # Check if reserved
        if SeatReservation.objects.filter(
            show=show,
            seat=self,
            status='RESERVED',
            expires_at__gt=timezone.now()
        ).exists():
            return 'RESERVED'
        
        # Check if locked
        if SeatLock.objects.filter(
            show=show,
            seat=self,
            expires_at__gt=timezone.now()
        ).exists():
            return 'LOCKED'
        
        return 'AVAILABLE'


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    seat = models.OneToOneField(Seat, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE)
    booked_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'Booking by {self.user.username} for {self.seat.seat_number} at {self.theater.name}'


# ============================================
# NEW MODELS ADDED FOR TASK FEATURES
# ============================================

class Genre(models.Model):
    """Movie genre/category"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class Language(models.Model):
    """Movie language"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)  # e.g., 'en', 'hi', 'ta'
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class Cast(models.Model):
    """Movie cast members"""
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    bio = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to='cast_photos/', blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    birth_date = models.DateField(blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class Review(models.Model):
    """Review and Rating system for movies"""
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    review_text = models.TextField()
    is_approved = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)  # Verified viewer badge
    is_reported = models.BooleanField(default=False)
    report_reason = models.CharField(max_length=200, blank=True, null=True)
    reported_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.movie.name} - {self.rating}⭐"
    
    def save(self, *args, **kwargs):
        # Auto-verify if user has booked a ticket for this movie
        if not self.is_verified and self.user.booking_set.filter(
            movie=self.movie,
        ).exists():
            self.is_verified = True
        super().save(*args, **kwargs)
    
    def can_edit(self, user):
        """Check if user can edit this review"""
        return user == self.user
    
    class Meta:
        unique_together = ['movie', 'user']  # One review per user per movie
        ordering = ['-created_at']


class ReviewReport(models.Model):
    """Report inappropriate reviews"""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['review', 'reported_by']


class MovieCast(models.Model):
    """Relationship between movies and cast with roles"""
    ROLE_CHOICES = [
        ('ACTOR', 'Actor'),
        ('DIRECTOR', 'Director'),
        ('PRODUCER', 'Producer'),
        ('WRITER', 'Writer'),
    ]
    
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='movie_cast')
    cast = models.ForeignKey(Cast, on_delete=models.CASCADE, related_name='movie_roles')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    character_name = models.CharField(max_length=200, blank=True, null=True)
    is_lead = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        unique_together = ['movie', 'cast', 'role']


class Screen(models.Model):
    """Screen within a theater"""
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='screens')
    screen_number = models.PositiveIntegerField()
    capacity = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.theater.name} - Screen {self.screen_number}"
    
    class Meta:
        unique_together = ['theater', 'screen_number']
        ordering = ['screen_number']


class Show(models.Model):
    """Movie show schedule"""
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    ]
    
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='shows')
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='shows')
    show_date = models.DateField()
    show_time = models.TimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.movie.name} - {self.show_date} {self.show_time}"
    
    def is_upcoming(self):
        from django.conf import settings
        show_datetime = timezone.datetime.combine(self.show_date, self.show_time)
        if settings.USE_TZ and timezone.is_naive(show_datetime):
            show_datetime = timezone.make_aware(show_datetime, timezone.get_current_timezone())
        return show_datetime > timezone.now()
    
    def get_available_seats(self):
        """Get number of available seats"""
        booked = self.bookings.filter(status='CONFIRMED').aggregate(models.Sum('seats'))['seats__sum'] or 0
        return self.screen.capacity - booked
    
    # ========== SMART SEAT RESERVATION METHODS ==========
    
    def get_available_seats_live(self):
        """Get available seats with live status"""
        from django.utils import timezone
        from django.db.models import Sum
        
        # Get all seats for this show's theater
        all_seats = self.screen.theater.seats.all()
        
        # Get booked seat IDs - FIXED: Use Booking model instead of ShowBooking
        booked_seat_ids = []
        
        # Get confirmed bookings from Booking model (not ShowBooking)
        confirmed_bookings = Booking.objects.filter(
            movie=self.movie,
            theater=self.screen.theater
        )
        
        if confirmed_bookings.exists():
            # Get all booked seat IDs
            booked_seat_ids = confirmed_bookings.values_list('seat__id', flat=True)
        
        # Get reserved seat IDs (active reservations)
        active_reservations = SeatReservation.objects.filter(
            show=self,
            status='RESERVED',
            expires_at__gt=timezone.now()
        ).values_list('seat__id', flat=True)
        
        # Get locked seat IDs
        active_locks = SeatLock.objects.filter(
            show=self,
            expires_at__gt=timezone.now()
        ).values_list('seat__id', flat=True)
        
        seat_status = {}
        for seat in all_seats:
            if seat.id in booked_seat_ids:
                seat_status[seat.id] = 'BOOKED'
            elif seat.id in active_reservations:
                seat_status[seat.id] = 'RESERVED'
            elif seat.id in active_locks:
                seat_status[seat.id] = 'LOCKED'
            else:
                seat_status[seat.id] = 'AVAILABLE'
        
        return seat_status
    
    def get_available_seats_count(self):
        """Get count of available seats"""
        from django.utils import timezone
        
        total = self.screen.capacity
        
        # Count booked seats from Booking model
        booked = Booking.objects.filter(
            movie=self.movie,
            theater=self.screen.theater
        ).count()
        
        # Count reserved seats (active)
        reserved = SeatReservation.objects.filter(
            show=self,
            status='RESERVED',
            expires_at__gt=timezone.now()
        ).count()
        
        # Count locked seats
        locked = SeatLock.objects.filter(
            show=self,
            expires_at__gt=timezone.now()
        ).count()
        
        return total - booked - reserved - locked
    
    def lock_seats(self, user, seat_ids, session_key=None):
        """Lock selected seats for reservation"""
        from django.utils import timezone
        from datetime import timedelta
        from django.db import transaction
        from django.db.models import Q
        
        with transaction.atomic():
            # Check if seats are already locked or booked
            locked_seats = SeatLock.objects.filter(
                show=self,
                seat__id__in=seat_ids,
                expires_at__gt=timezone.now()
            ).exists()
            
            if locked_seats:
                return False, "Some seats are already locked by another user"
            
            # Check if seats are already booked
            booked_seats = Booking.objects.filter(
                seat__id__in=seat_ids
            ).exists()
            
            if booked_seats:
                return False, "Some seats are already booked"
            
            # Create locks for each seat
            expires_at = timezone.now() + timedelta(minutes=2)  # 2 minute lock
            
            for seat_id in seat_ids:
                SeatLock.objects.create(
                    user=user,
                    show=self,
                    seat_id=seat_id,
                    expires_at=expires_at,
                    session_key=session_key
                )
            
            return True, "Seats locked successfully"
    
    def reserve_seats(self, user, seat_ids):
        """Reserve seats (convert lock to reservation)"""
        from django.utils import timezone
        from datetime import timedelta
        from django.db import transaction
        
        with transaction.atomic():
            # Get locks for these seats
            locks = SeatLock.objects.filter(
                show=self,
                user=user,
                seat__id__in=seat_ids,
                expires_at__gt=timezone.now()
            )
            
            if locks.count() != len(seat_ids):
                return False, "Some seats are no longer locked"
            
            expires_at = timezone.now() + timedelta(minutes=2)  # 2 minute reservation
            
            reservations = []
            for lock in locks:
                reservation = SeatReservation.objects.create(
                    user=user,
                    show=self,
                    seat=lock.seat,
                    expires_at=expires_at,
                    status='RESERVED'
                )
                reservations.append(reservation)
                lock.delete()  # Remove lock after reservation
            
            return True, "Seats reserved successfully"
    
    def confirm_booking_from_reservation(self, user, reservation_ids, booking_data):
        """Confirm booking from reservations"""
        from django.db import transaction
        from django.utils import timezone
        
        with transaction.atomic():
            reservations = SeatReservation.objects.filter(
                id__in=reservation_ids,
                user=user,
                show=self,
                status='RESERVED',
                expires_at__gt=timezone.now()
            )
            
            if reservations.count() != len(reservation_ids):
                return None, "Some reservations have expired"
            
            # Create booking using Booking model (not ShowBooking)
            booking = Booking.objects.create(
                user=user,
                seat=reservations.first().seat,
                movie=self.movie,
                theater=self.screen.theater
            )
            
            # Mark reservations as booked
            for reservation in reservations:
                reservation.book(booking)
            
            return booking, "Booking confirmed successfully"
    
    class Meta:
        ordering = ['show_date', 'show_time']


class ShowBooking(models.Model):
    """Enhanced booking system with multiple seats"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='show_bookings')
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='bookings')
    seats = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    def __str__(self):
        return f"{self.user.username} - {self.show.movie.name} - {self.seats} seats"
    
    def can_review(self):
        """Check if user can review this movie"""
        if self.status == 'CONFIRMED' and self.show.show_date <= timezone.now().date():
            return True
        return False
    
    class Meta:
        ordering = ['-booking_date']


# ============================================
# SMART SEAT RESERVATION MODELS
# ============================================

class SeatReservation(models.Model):
    """Temporary seat reservation with timeout"""
    STATUS_CHOICES = [
        ('RESERVED', 'Reserved'),
        ('BOOKED', 'Booked'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='seat_reservations')
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='seat_reservations')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='reservations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RESERVED')
    reserved_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='seat_reservations')
    
    class Meta:
        unique_together = ['show', 'seat', 'status']  # Prevent duplicate reservations
        ordering = ['-reserved_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.show.movie.name} - Seat {self.seat.seat_number} - {self.status}"
    
    def is_expired(self):
        """Check if reservation has expired"""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def can_be_booked(self):
        """Check if reservation can be converted to booking"""
        return self.status == 'RESERVED' and not self.is_expired()
    
    def expire(self):
        """Expire the reservation"""
        self.status = 'EXPIRED'
        self.save()
    
    def book(self, booking):
        """Convert reservation to booking"""
        self.status = 'BOOKED'
        self.booking = booking
        self.save()


class SeatLock(models.Model):
    """Track temporarily locked seats for live reservation"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='seat_locks')
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='seat_locks')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='seat_locks')
    locked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    session_key = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.seat.seat_number} - Locked at {self.locked_at}"
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    class Meta:
        unique_together = ['show', 'seat']  # Prevent duplicate locks
        ordering = ['-locked_at']

# ============================================
# PAYMENT MODELS - ADD TO movies/models.py
# ============================================

class Payment(models.Model):
    """Payment transaction model"""
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
        ('ATTEMPTED', 'Attempted'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('RAZORPAY', 'Razorpay'),
        ('STRIPE', 'Stripe'),
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    booking = models.ForeignKey('ShowBooking', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='RAZORPAY')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    
    # Transaction IDs
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    
    # Failure details
    failure_reason = models.TextField(blank=True, null=True)
    failure_code = models.CharField(max_length=50, blank=True, null=True)
    
    # Webhook tracking
    webhook_processed = models.BooleanField(default=False)
    webhook_processed_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - ₹{self.amount} - {self.payment_status}"
    
    def mark_success(self, payment_id, signature):
        """Mark payment as success"""
        self.payment_status = 'SUCCESS'
        self.razorpay_payment_id = payment_id
        self.razorpay_signature = signature
        self.paid_at = timezone.now()
        self.save()
        
        # Confirm the booking
        if self.booking:
            self.booking.status = 'CONFIRMED'
            self.booking.save()
        
        return True
    
    def mark_failed(self, reason=None, code=None):
        """Mark payment as failed"""
        self.payment_status = 'FAILED'
        self.failure_reason = reason
        self.failure_code = code
        self.save()
        
        # Release reserved seats
        if self.booking:
            # Release seats
            Seat.objects.filter(
                id__in=self.booking.seat_ids if hasattr(self.booking, 'seat_ids') else []
            ).update(is_booked=False)
            self.booking.status = 'CANCELLED'
            self.booking.save()
        
        return True
    
    def mark_cancelled(self):
        """Mark payment as cancelled"""
        self.payment_status = 'CANCELLED'
        self.save()
        
        # Release reserved seats
        if self.booking:
            Seat.objects.filter(
                id__in=self.booking.seat_ids if hasattr(self.booking, 'seat_ids') else []
            ).update(is_booked=False)
            self.booking.status = 'CANCELLED'
            self.booking.save()
        
        return True
    
    class Meta:
        ordering = ['-created_at']

# ============================================
# ANALYTICS MODELS - ADD TO movies/models.py
# ============================================

class AnalyticsEvent(models.Model):
    """Track user actions for analytics"""
    EVENT_TYPES = [
        ('VIEW', 'Page View'),
        ('BOOKING', 'Booking Created'),
        ('PAYMENT', 'Payment Completed'),
        ('CANCELLATION', 'Booking Cancelled'),
        ('REFUND', 'Refund Processed'),
        ('SEARCH', 'Search Performed'),
        ('REVIEW', 'Review Submitted'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    movie = models.ForeignKey('Movie', on_delete=models.SET_NULL, null=True, blank=True)
    theater = models.ForeignKey('Theater', on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['movie', 'created_at']),
            models.Index(fields=['theater', 'created_at']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.created_at}"


class DailyReport(models.Model):
    """Daily aggregated analytics report"""
    date = models.DateField(unique=True)
    total_bookings = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cancellations = models.IntegerField(default=0)
    total_refunds = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unique_users = models.IntegerField(default=0)
    new_users = models.IntegerField(default=0)
    avg_booking_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    occupancy_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['date']),
        ]
        ordering = ['-date']
    
    def __str__(self):
        return f"Report for {self.date}"     
# ============================================
# TICKET MODELS - ADD TO movies/models.py
# ============================================

class Ticket(models.Model):
    """Ticket model for generated tickets"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('GENERATED', 'Generated'),
        ('EMAIL_SENT', 'Email Sent'),
        ('EMAIL_FAILED', 'Email Failed'),
        ('DOWNLOADED', 'Downloaded'),
    ]
    
    booking = models.OneToOneField('ShowBooking', on_delete=models.CASCADE, related_name='ticket')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    
    # Ticket details
    ticket_number = models.CharField(max_length=50, unique=True)
    qr_code = models.ImageField(upload_to='tickets/qr_codes/', blank=True, null=True)
    pdf_file = models.FileField(upload_to='tickets/pdfs/', blank=True, null=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    generated_at = models.DateTimeField(auto_now_add=True)
    email_sent_at = models.DateTimeField(blank=True, null=True)
    downloaded_at = models.DateTimeField(blank=True, null=True)
    
    # Retry tracking
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    last_error = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.booking.show.movie.name}"
    
    def mark_generated(self):
        self.status = 'GENERATED'
        self.save()
    
    def mark_email_sent(self):
        self.status = 'EMAIL_SENT'
        self.email_sent_at = timezone.now()
        self.save()
    
    def mark_email_failed(self, error=None):
        self.status = 'EMAIL_FAILED'
        self.retry_count += 1
        self.last_error = error
        self.save()
    
    def mark_downloaded(self):
        self.status = 'DOWNLOADED'
        self.downloaded_at = timezone.now()
        self.save()
    
    def can_retry(self):
        return self.retry_count < self.max_retries
    
    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['ticket_number']),
            models.Index(fields=['status']),
        ]       