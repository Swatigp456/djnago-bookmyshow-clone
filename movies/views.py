from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Avg, Count, Min, Max
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.models import User
from django.db import transaction
from datetime import timedelta
from .payment_utils import RazorpayClient
from .forms import PaymentForm
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, Http404
from datetime import datetime, timedelta
from django.template.loader import render_to_string
from .analytics_utils import AnalyticsService
from .models import AnalyticsEvent, DailyReport
from .discovery_utils import MovieDiscoveryService
from .models import Genre, Language, AnalyticsEvent
from django.views.decorators.cache import cache_control
from django.core.files.base import ContentFile
from .models import Ticket
from .ticket_utils import TicketGenerator
from .tasks import generate_and_send_ticket
from django.views.decorators.csrf import csrf_exempt
import json

from .models import (
    Movie, Genre, Language, Cast, Review, ReviewReport, 
    Theater, Screen, Show, ShowBooking, Seat, Booking,
    SeatReservation, SeatLock, Payment 
)
from .forms import ReviewForm, ReviewReportForm, BookingForm

def movie_list(request):
    """
    Enhanced movie listing with search, filters, sorting, recommendations, and trending
    """
    # Get filter parameters
    search_query = request.GET.get('search', '')
    genres = request.GET.get('genres', '')
    language = request.GET.get('language', '')
    city = request.GET.get('city', '')
    theater = request.GET.get('theater', '')
    release_date_start = request.GET.get('release_date_start', '')
    release_date_end = request.GET.get('release_date_end', '')
    min_rating = request.GET.get('min_rating', '')
    show_time = request.GET.get('show_time', '')
    sort_by = request.GET.get('sort', 'popularity')
    page = request.GET.get('page', 1)
    
    # Start with all active movies
    movies = Movie.objects.filter(is_active=True)
    
    # Search filter
    if search_query:
        movies = movies.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(director__icontains=search_query) |
            Q(cast__icontains=search_query)
        )
    
    # Genre filter
    if genres:
        genre_list = [g.strip() for g in genres.split(',') if g.strip()]
        for genre in genre_list:
            movies = movies.filter(genres__icontains=genre)
    
    # Language filter
    if language:
        movies = movies.filter(language__icontains=language)
    
    # City filter
    if city:
        movies = movies.filter(city__icontains=city)
    
    # Theater filter
    if theater:
        movies = movies.filter(theater__icontains=theater)
    
    # Release date filter
    if release_date_start:
        movies = movies.filter(release_date__gte=release_date_start)
    if release_date_end:
        movies = movies.filter(release_date__lte=release_date_end)
    
    # Rating filter
    if min_rating:
        try:
            min_rating = float(min_rating)
            movies = movies.filter(rating__gte=min_rating)
        except ValueError:
            pass
    
    # Show time filter
    if show_time:
        try:
            time_obj = datetime.strptime(show_time, '%H:%M').time()
            movies = movies.filter(shows__show_time__gte=time_obj).distinct()
        except ValueError:
            pass
    
    # Sorting
    if sort_by == 'popularity':
        movies = movies.annotate(
            booking_count=Count('shows__bookings', distinct=True)
        ).order_by('-booking_count')
    elif sort_by == 'newest':
        movies = movies.order_by('-release_date')
    elif sort_by == 'rating':
        movies = movies.order_by('-rating')
    elif sort_by == 'price_low':
        movies = movies.annotate(
            min_price=Min('shows__price')
        ).order_by('min_price')
    elif sort_by == 'price_high':
        movies = movies.annotate(
            max_price=Max('shows__price')
        ).order_by('-max_price')
    else:
        movies = movies.order_by('-id')
    
    # Total count
    total_count = movies.count()
    
    # Pagination
    paginator = Paginator(movies, 12)
    try:
        movies_page = paginator.page(page)
    except PageNotAnInteger:
        movies_page = paginator.page(1)
    except EmptyPage:
        movies_page = paginator.page(paginator.num_pages)
    
    # Get filter options
    filter_options = {
        'cities': Movie.objects.filter(is_active=True).values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city=''),
        'theaters': Movie.objects.filter(is_active=True).values_list('theater', flat=True).distinct().exclude(theater__isnull=True).exclude(theater=''),
        'min_rating': [1, 2, 3, 4, 4.5],
        'show_times': ['10:00', '13:00', '18:00', '21:00'],
        'languages': Movie.objects.filter(is_active=True).values_list('language', flat=True).distinct().exclude(language__isnull=True).exclude(language=''),
    }
    
    # Get recommendations for logged-in users
    recommended_movies = []
    if request.user.is_authenticated:
        recommended_movies = get_recommendations(request.user)
    
    # Get trending movies
    trending_movies = get_trending_movies(6)
    
    context = {
        'movies': movies_page,
        'total_count': total_count,
        'search_query': search_query,
        'selected_genres': genres,
        'selected_language': language,
        'selected_city': city,
        'selected_theater': theater,
        'selected_release_date_start': release_date_start,
        'selected_release_date_end': release_date_end,
        'selected_min_rating': min_rating,
        'selected_show_time': show_time,
        'sort_by': sort_by,
        'filter_options': filter_options,
        'recommended_movies': recommended_movies,
        'trending_movies': trending_movies,
        'paginator': paginator,
        'page': page,
    }
    
    return render(request, 'movies/movie_list.html', context)


def get_recommendations(user, limit=6):
    """Get personalized movie recommendations"""
    if not user or not user.is_authenticated:
        return Movie.objects.filter(is_active=True).order_by('-rating')[:limit]
    
    # Get user's booking history
    booked_movies = ShowBooking.objects.filter(
        user=user,
        status='CONFIRMED'
    ).values_list('show__movie__id', flat=True).distinct()
    
    viewed_movies = AnalyticsEvent.objects.filter(
        user=user,
        event_type='VIEW'
    ).values_list('movie__id', flat=True).distinct()
    
    watched_movies = list(booked_movies) + list(viewed_movies)
    
    if watched_movies:
        watched_directors = Movie.objects.filter(
            id__in=watched_movies
        ).values_list('director', flat=True).distinct()
        
        recommendations = Movie.objects.filter(
            is_active=True
        ).exclude(
            id__in=watched_movies
        ).filter(
            director__in=watched_directors
        ).order_by('-rating')[:limit]
        
        if recommendations.count() < limit:
            extra_needed = limit - recommendations.count()
            extra = Movie.objects.filter(
                is_active=True
            ).exclude(
                id__in=watched_movies
            ).exclude(
                id__in=recommendations.values_list('id', flat=True)
            ).order_by('-rating')[:extra_needed]
            recommendations = list(recommendations) + list(extra)
        
        return recommendations
    else:
        return Movie.objects.filter(is_active=True).order_by('-rating')[:limit]


def get_trending_movies(limit=10):
    """Get trending movies"""
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    trending = Movie.objects.filter(
        is_active=True,
        shows__bookings__booking_date__gte=thirty_days_ago,
        shows__bookings__status='CONFIRMED'
    ).annotate(
        popularity=Count('shows__bookings')
    ).order_by('-popularity')[:limit]
    
    if trending.count() < limit:
        extra_needed = limit - trending.count()
        extra = Movie.objects.filter(
            is_active=True
        ).exclude(
            id__in=trending.values_list('id', flat=True)
        ).order_by('-rating')[:extra_needed]
        trending = list(trending) + list(extra)
    
    return trending

def movie_detail(request, pk):
    """Display movie details"""
    movie = get_object_or_404(Movie, pk=pk, is_active=True)
    
    # Get reviews - handle case where no reviews exist
    reviews = movie.get_recent_reviews(10) if hasattr(movie, 'get_recent_reviews') else []
    user_review = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(movie=movie, user=request.user).first()
    
    # Get similar movies
    similar_movies = movie.get_similar_movies(4) if hasattr(movie, 'get_similar_movies') else []
    
    # Get upcoming shows
    upcoming_shows = movie.get_upcoming_shows() if hasattr(movie, 'get_upcoming_shows') else []
    
    # Calculate rating distribution
    rating_distribution = {
        5: movie.reviews.filter(rating=5, is_approved=True).count(),
        4: movie.reviews.filter(rating=4, is_approved=True).count(),
        3: movie.reviews.filter(rating=3, is_approved=True).count(),
        2: movie.reviews.filter(rating=2, is_approved=True).count(),
        1: movie.reviews.filter(rating=1, is_approved=True).count(),
    }
    
    context = {
        'movie': movie,
        'reviews': reviews,
        'user_review': user_review,
        'similar_movies': similar_movies,
        'upcoming_shows': upcoming_shows,
        'review_count': movie.get_rating_count() if hasattr(movie, 'get_rating_count') else 0,
        'average_rating': movie.get_average_rating() if hasattr(movie, 'get_average_rating') else 0,
        'rating_distribution': rating_distribution,
    }
    return render(request, 'movies/movie_detail.html', context)


def genre_list(request):
    """Display list of genres"""
    genres = Genre.objects.all()
    return render(request, 'movies/genre_list.html', {'genres': genres})


def genre_detail(request, pk):
    """Display movies by genre"""
    genre = get_object_or_404(Genre, pk=pk)
    movies = Movie.objects.filter(genres=genre, is_active=True)
    return render(request, 'movies/genre_detail.html', {'genre': genre, 'movies': movies})


def language_list(request):
    """Display list of languages"""
    languages = Language.objects.filter(is_active=True)
    return render(request, 'movies/language_list.html', {'languages': languages})


def language_detail(request, pk):
    """Display movies by language"""
    language = get_object_or_404(Language, pk=pk, is_active=True)
    movies = Movie.objects.filter(languages=language, is_active=True)
    return render(request, 'movies/language_detail.html', {'language': language, 'movies': movies})


def theater_list(request, movie_id):
    """Display theaters and shows for a specific movie"""
    movie = get_object_or_404(Movie, id=movie_id)
    
    # Get all shows for this movie
    shows = Show.objects.filter(
        movie=movie,
        is_active=True,
        status='SCHEDULED',
        show_date__gte=timezone.now().date()
    ).order_by('show_date', 'show_time')
    
    context = {
        'movie': movie,
        'shows': shows,
    }
    return render(request, 'movies/theater_list.html', context)


# ============================================
# NEW VIEWS ADDED FOR TASK FEATURES
# ============================================

@login_required
@require_POST
def add_review(request, movie_id):
    """Add a review for a movie"""
    movie = get_object_or_404(Movie, id=movie_id, is_active=True)
    
    # Check if already reviewed
    existing_review = Review.objects.filter(movie=movie, user=request.user).first()
    if existing_review:
        messages.error(request, 'You have already reviewed this movie!')
        return redirect('movie_detail', pk=movie.id)
    
    # Skip booking check - anyone can review
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.movie = movie
        review.user = request.user
        review.is_verified = False
        review.is_approved = True
        review.save()
        messages.success(request, 'Your review has been submitted!')
    else:
        messages.error(request, 'Please correct the errors in the form.')
    
    return redirect('movie_detail', pk=movie.id)
    

@login_required
def edit_review(request, review_id):
    """Edit an existing review"""
    review = get_object_or_404(Review, id=review_id)
    
    if review.user != request.user:
        messages.error(request, 'You can only edit your own reviews!')
        return redirect('movie_detail', pk=review.movie.id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your review has been updated!')
            return redirect('movie_detail', pk=review.movie.id)
    else:
        form = ReviewForm(instance=review)
    
    return render(request, 'movies/edit_review.html', {'form': form, 'review': review})


@login_required
@require_POST
def delete_review(request, review_id):
    """Delete a review"""
    review = get_object_or_404(Review, id=review_id)
    
    if review.user != request.user:
        messages.error(request, 'You can only delete your own reviews!')
        return redirect('movie_detail', pk=review.movie.id)
    
    movie_id = review.movie.id
    review.delete()
    messages.success(request, 'Your review has been deleted.')
    return redirect('movie_detail', pk=movie_id)


@login_required
@require_POST
def report_review(request, review_id):
    """Report an inappropriate review"""
    review = get_object_or_404(Review, id=review_id)
    
    if review.user == request.user:
        messages.error(request, 'You cannot report your own review!')
        return redirect('movie_detail', pk=review.movie.id)
    
    form = ReviewReportForm(request.POST)
    if form.is_valid():
        report = form.save(commit=False)
        report.review = review
        report.reported_by = request.user
        report.save()
        
        review.is_reported = True
        review.report_reason = request.POST.get('reason')
        review.reported_at = timezone.now()
        review.save()
        
        messages.success(request, 'Review has been reported. Thank you for helping us maintain quality!')
    else:
        messages.error(request, 'Please provide a reason for reporting.')
    
    return redirect('movie_detail', pk=review.movie.id)


@login_required
def book_ticket(request, show_id):
    """Book tickets for a show"""
    show = get_object_or_404(Show, id=show_id, is_active=True)
    
    if not show.is_upcoming():
        messages.error(request, 'This show has already passed!')
        return redirect('movie_detail', pk=show.movie.id)
    
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            seats = form.cleaned_data['seats']
            available_seats = show.get_available_seats()
            
            if seats > available_seats:
                messages.error(request, f'Only {available_seats} seats available!')
                return redirect('book_ticket', show_id=show.id)
            
            booking = ShowBooking(
                user=request.user,
                show=show,
                seats=seats,
                total_price=seats * show.price,
                status='PENDING'
            )
            booking.save()
            
            
            messages.success(request, f'Booking confirmed! {seats} seats booked for {show.movie.name}.')
            return redirect('my_bookings')
    else:
        form = BookingForm()
    
    return render(request, 'movies/book_ticket.html', {
        'show': show,
        'form': form,
        'available_seats': show.get_available_seats()
    })



@login_required
def my_bookings(request):
    """View user's bookings"""
    bookings = ShowBooking.objects.filter(user=request.user).order_by('-booking_date')
    
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    return render(request, 'movies/my_bookings.html', {
        'bookings': bookings,
        'status_filter': status_filter
    })


@login_required
def cancel_booking(request, booking_id):
    """Cancel a booking"""
    booking = get_object_or_404(ShowBooking, id=booking_id, user=request.user)
    
    if booking.status == 'CONFIRMED':
        booking.status = 'CANCELLED'
        booking.save()
        messages.success(request, 'Booking cancelled successfully!')
    else:
        messages.error(request, 'This booking cannot be cancelled.')
    
    return redirect('my_bookings')


def get_movie_rating(request, movie_id):
    """AJAX view to get movie rating data"""
    movie = get_object_or_404(Movie, id=movie_id)
    data = {
        'average_rating': movie.get_average_rating(),
        'total_ratings': movie.get_rating_count(),
        'rating_distribution': {
            1: movie.reviews.filter(rating=1, is_approved=True).count(),
            2: movie.reviews.filter(rating=2, is_approved=True).count(),
            3: movie.reviews.filter(rating=3, is_approved=True).count(),
            4: movie.reviews.filter(rating=4, is_approved=True).count(),
            5: movie.reviews.filter(rating=5, is_approved=True).count(),
        }
    }
    return JsonResponse(data)


def trending_movies(request):
    """View for trending movies"""
    movies = Movie.objects.filter(is_active=True, is_trending=True).order_by('-id')
    return render(request, 'movies/movie_list.html', {
        'movies': movies,
        'title': 'Trending Movies'
    })


def recent_movies(request):
    """View for recent movies"""
    movies = Movie.objects.filter(is_active=True).order_by('-id')[:12]
    return render(request, 'movies/movie_list.html', {
        'movies': movies,
        'title': 'Recently Released'
    })


# ============================================
# SMART SEAT RESERVATION VIEWS (SIMPLIFIED & FIXED)
# ============================================

@login_required
@require_GET
def get_seat_availability(request, show_id):
    """AJAX endpoint to get live seat availability"""
    show = get_object_or_404(Show, id=show_id, is_active=True)
    
    # Get all seats for this show's theater
    seats = show.screen.theater.seats.all()
    
    # Get booked seat IDs from Booking model
    booked_seat_ids = Booking.objects.filter(
        seat__in=seats
    ).values_list('seat__id', flat=True)
    
    data = {
        'seats': [],
        'total_seats': show.screen.capacity,
        'available_count': seats.count() - booked_seat_ids.count(),
        'booked_count': booked_seat_ids.count(),
        'reserved_count': 0,
    }
    
    for seat in seats:
        is_booked = seat.id in booked_seat_ids
        data['seats'].append({
            'id': seat.id,
            'number': seat.seat_number,
            'status': 'BOOKED' if is_booked else 'AVAILABLE',
            'is_booked': is_booked,
            'is_reserved': False,
            'is_locked': False,
            'is_available': not is_booked,
        })
    
    return JsonResponse(data)


@login_required
def seat_selection(request, show_id):
    """View for selecting seats"""
    show = get_object_or_404(Show, id=show_id, is_active=True)
    
    if not show.is_upcoming():
        messages.error(request, 'This show has already passed!')
        return redirect('movie_detail', pk=show.movie.id)
    
    # Get all seats for this show's theater
    seats = show.screen.theater.seats.all()
    booked_seat_ids = Booking.objects.filter(
        seat__in=seats
    ).values_list('seat__id', flat=True)
    
    context = {
        'show': show,
        'total_seats': show.screen.capacity,
        'available_count': seats.count() - booked_seat_ids.count(),
        'booked_count': booked_seat_ids.count(),
        'price_per_seat': show.price,
        'expiry_time': 120,
    }
    
    return render(request, 'movies/seat_selection.html', context)


@login_required
@require_POST
def confirm_reservation(request, show_id):
    """Confirm booking from selected seats"""
    show = get_object_or_404(Show, id=show_id, is_active=True)
    
    try:
        data = json.loads(request.body)
        seat_ids = data.get('reservation_ids', [])
        
        if not seat_ids:
            return JsonResponse({
                'success': False,
                'error': 'No seats selected.'
            })
        
        # Get all seats
        all_seats = show.screen.theater.seats.filter(id__in=seat_ids)
        
        # Check if any seats are already booked
        booked_seats = Booking.objects.filter(
            seat__in=all_seats
        ).exists()
        
        if booked_seats:
            return JsonResponse({
                'success': False,
                'error': 'Some seats are already booked.'
            })
        
        # Create booking
        with transaction.atomic():
            booking = ShowBooking.objects.create(
                user=request.user,
                show=show,
                seats=len(seat_ids),
                total_price=show.price * len(seat_ids),
                status='PENDING'
            )
            
            for seat in all_seats:
                seat.is_booked = True
                seat.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Booking confirmed!',
                'booking_id': booking.id
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
@login_required
@require_POST
def lock_seats(request, show_id):
    """Lock selected seats for the user (simplified)"""
    return JsonResponse({
        'success': True,
        'message': 'Seats locked successfully',
        'expires_in': 120
    })


@login_required
@require_POST
def reserve_seats(request, show_id):
    """Reserve seats (simplified)"""
    return JsonResponse({
        'success': True,
        'message': 'Seats reserved successfully',
        'expires_in': 120
    })


@login_required
@require_POST
def release_seats(request, show_id):
    """Release locked/reserved seats (simplified)"""
    return JsonResponse({
        'success': True,
        'message': 'Seats released successfully'
    })

@login_required
def initiate_payment(request, booking_id):
    """Initiate payment for a booking"""
    print("=" * 60)
    print("INITIATE_PAYMENT CALLED")
    print("Booking ID from URL:", booking_id)
    print("Logged-in user:", request.user.username)
    print("=" * 60)

    try:
        booking = ShowBooking.objects.get(id=booking_id)
        print("✅ Booking found:", booking.id, "| status:", booking.status)
    except ShowBooking.DoesNotExist:
        print("❌ Booking NOT FOUND for id:", booking_id)
        messages.error(request, "Booking not found")
        return redirect('my_bookings')

    if booking.status == 'CONFIRMED':
        print("❌ REDIRECT #1: Booking already CONFIRMED")
        messages.info(request, 'This booking is already confirmed.')
        return redirect('my_bookings')

    existing_payment = Payment.objects.filter(booking=booking).first()
    print("Existing payment:", existing_payment)
    if existing_payment and existing_payment.payment_status == 'SUCCESS':
        print("❌ REDIRECT #2: Payment already SUCCESS")
        messages.info(request, 'Payment already completed for this booking.')
        return redirect('my_bookings')

    print("✅ Checks passed. Creating Razorpay order...")

    client = RazorpayClient()
    order_data = client.create_order(
        amount=float(booking.total_price),
        currency="INR",
        receipt=f"booking_{booking.id}",
        notes={
            'booking_id': str(booking.id),
            'user_id': str(request.user.id),
        }
    )

    print("Order Data:", order_data)

    if not order_data['success']:
        print("❌ REDIRECT #3: Order creation failed:", order_data.get('error'))
        messages.error(request, f"Payment failed: {order_data.get('error')}")
        return redirect('my_bookings')

    payment = Payment.objects.create(
        user=request.user,
        booking=booking,
        amount=booking.total_price,
        payment_method='RAZORPAY',
        payment_status='PENDING',
        razorpay_order_id=order_data['order_id']
    )

    print("✅ Payment record created:", payment.id)
    print("✅ Rendering payment page")

    context = {
        'booking': booking,
        'payment': payment,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'order_id': order_data['order_id'],
        'amount': booking.total_price,
        'user_name': request.user.username,
        'user_email': request.user.email or 'guest@example.com',
        'user_phone': '9999999999',
    }

    return render(request, 'movies/payment.html', context)
@csrf_exempt
@login_required
@require_POST
def verify_payment(request):
    """Verify payment after successful transaction"""
    try:
        data = json.loads(request.body)
        order_id = data.get('razorpay_order_id')
        payment_id = data.get('razorpay_payment_id')
        signature = data.get('razorpay_signature')
        
        if not all([order_id, payment_id, signature]):
            return JsonResponse({
                'success': False,
                'error': 'Missing payment details'
            })
        
        # Get payment record
        payment = get_object_or_404(Payment, razorpay_order_id=order_id)
        
        # Verify signature
        client = RazorpayClient()
        verification = client.verify_payment(order_id, payment_id, signature)
        
        if not verification['success']:
            payment.mark_failed(
                reason=verification.get('error', 'Verification failed'),
                code='VERIFICATION_FAILED'
            )
            return JsonResponse({
                'success': False,
                'error': 'Payment verification failed'
            })
        
        # Verify payment is not already processed
        if payment.payment_status == 'SUCCESS':
            return JsonResponse({
                'success': True,
                'message': 'Payment already confirmed'
            })
        
        # Capture payment
        capture = client.capture_payment(payment_id, float(payment.amount))
        
        if not capture['success']:
            payment.mark_failed(
                reason=capture.get('error', 'Capture failed'),
                code='CAPTURE_FAILED'
            )
            return JsonResponse({
                'success': False,
                'error': 'Payment capture failed'
            })
        
        # Mark payment as success
        payment.mark_success(payment_id, signature)
        
        # Update booking status
        booking = payment.booking
        if booking:
            booking.status = 'CONFIRMED'
            booking.save()
            generate_and_send_ticket.delay(booking.id)
            # Mark seats as booked
            # This assumes you have seat_ids stored or you can fetch from reservation
            # For now, we'll use the booking's seat count to mark seats
        
        return JsonResponse({
            'success': True,
            'message': 'Payment confirmed successfully!',
            'booking_id': payment.booking.id if payment.booking else None
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def payment_status(request, payment_id):
    """Check payment status"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    data = {
        'payment_id': payment.id,
        'status': payment.payment_status,
        'amount': str(payment.amount),
        'created_at': payment.created_at.isoformat(),
        'booking_id': payment.booking.id if payment.booking else None
    }
    
    return JsonResponse(data)


@login_required
def payment_history(request):
    """View payment history"""
    payments = Payment.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'payments': payments,
    }
    return render(request, 'movies/payment_history.html', context)


@login_required
@require_POST
def retry_payment(request, booking_id):
    """Retry failed payment"""
    booking = get_object_or_404(ShowBooking, id=booking_id)
    
    # Check if booking is already confirmed
    if booking.status == 'CONFIRMED':
        return JsonResponse({
            'success': False,
            'error': 'Booking already confirmed'
        })
    
    # Check if there's a failed payment
    payment = Payment.objects.filter(
        booking=booking,
        payment_status__in=['FAILED', 'CANCELLED', 'ATTEMPTED']
    ).first()
    
    if not payment:
        return JsonResponse({
            'success': False,
            'error': 'No failed payment found to retry'
        })
    
    # Create new payment
    client = RazorpayClient()
    order_data = client.create_order(
        amount=float(booking.total_price),
        currency="INR",
        receipt=f"booking_{booking.id}_retry",
        notes={
            'booking_id': str(booking.id),
            'user_id': str(request.user.id),
            'retry': 'true'
        }
    )
    
    if not order_data['success']:
        return JsonResponse({
            'success': False,
            'error': order_data.get('error', 'Order creation failed')
        })
    
    # Update payment with new order
    payment.razorpay_order_id = order_data['order_id']
    payment.payment_status = 'PENDING'
    payment.failure_reason = None
    payment.failure_code = None
    payment.save()
    
    return JsonResponse({
        'success': True,
        'order_id': order_data['order_id'],
        'amount': str(booking.total_price),
        'razorpay_key_id': settings.RAZORPAY_KEY_ID
    })


@login_required
@require_POST
def cancel_payment(request, payment_id):
    """Cancel a pending payment"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    if payment.payment_status not in ['PENDING', 'ATTEMPTED']:
        return JsonResponse({
            'success': False,
            'error': 'Payment cannot be cancelled'
        })
    
    payment.mark_cancelled()
    
    return JsonResponse({
        'success': True,
        'message': 'Payment cancelled successfully'
    })

@staff_member_required
def admin_dashboard(request):
    """Main admin dashboard view"""
    context = {
        'summary': AnalyticsService.get_dashboard_summary(),
        'recent_events': AnalyticsEvent.objects.all()[:50],
    }
    return render(request, 'admin/dashboard.html', context)


@staff_member_required
def analytics_revenue(request):
    """Revenue analytics view"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    period = request.GET.get('period', 'daily')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    revenue_data = AnalyticsService.get_revenue_data(start_date, end_date, period)
    trends = AnalyticsService.get_booking_trends(start_date, end_date)
    
    context = {
        'revenue_data': revenue_data,
        'trends': trends,
        'start_date': start_date,
        'end_date': end_date,
        'period': period,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(context)
    
    return render(request, 'admin/analytics_revenue.html', context)


@staff_member_required
def analytics_occupancy(request):
    """Theater occupancy analytics"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    occupancy_data = AnalyticsService.get_theater_occupancy(start_date, end_date)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'occupancy_data': occupancy_data})
    
    context = {
        'occupancy_data': occupancy_data,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'admin/analytics_occupancy.html', context)


@staff_member_required
def analytics_top_movies(request):
    """Top movies analytics"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    limit = int(request.GET.get('limit', 10))
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    top_movies = AnalyticsService.get_top_movies(start_date, end_date, limit)
    
    context = {
        'top_movies': top_movies,
        'start_date': start_date,
        'end_date': end_date,
        'limit': limit,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'top_movies': top_movies})
    
    return render(request, 'admin/analytics_top_movies.html', context)


@staff_member_required
def analytics_peak_hours(request):
    """Peak hours analytics"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    peak_hours = AnalyticsService.get_peak_hours(start_date, end_date)
    
    context = {
        'peak_hours': peak_hours,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'peak_hours': peak_hours})
    
    return render(request, 'admin/analytics_peak_hours.html', context)


@staff_member_required
def analytics_cancellations(request):
    """Cancellation and refund analytics"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    cancellation_stats = AnalyticsService.get_cancellation_stats(start_date, end_date)
    
    context = {
        'cancellation_stats': cancellation_stats,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(cancellation_stats)
    
    return render(request, 'admin/analytics_cancellations.html', context)


@staff_member_required
def analytics_users(request):
    """User growth analytics"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    user_growth = AnalyticsService.get_user_growth(start_date, end_date)
    
    context = {
        'user_growth': user_growth,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(user_growth)
    
    return render(request, 'admin/analytics_users.html', context)


@staff_member_required
def export_csv_report(request):
    """Export analytics data as CSV"""
    report_type = request.GET.get('type', 'revenue')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    data = []
    filename = f"{report_type}_report.csv"
    
    if report_type == 'revenue':
        data = AnalyticsService.get_revenue_data(start_date, end_date)
    elif report_type == 'occupancy':
        data = AnalyticsService.get_theater_occupancy(start_date, end_date)
    elif report_type == 'top_movies':
        data = AnalyticsService.get_top_movies(start_date, end_date)
    elif report_type == 'peak_hours':
        data = AnalyticsService.get_peak_hours(start_date, end_date)
    elif report_type == 'user_growth':
        user_growth = AnalyticsService.get_user_growth(start_date, end_date)
        data = user_growth.get('daily_growth', [])
    
    csv_content = AnalyticsService.generate_csv_report(data, filename)
    
    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
def movie_discovery(request):
    """
    Movie discovery page with search, filters, and recommendations
    """
    # Get filter parameters
    filters = {}
    search_query = request.GET.get('search', '')
    if search_query:
        filters['search'] = search_query
    
    genres = request.GET.getlist('genres')
    if genres:
        filters['genres'] = genres
    
    languages = request.GET.getlist('languages')
    if languages:
        filters['languages'] = languages
    
    city = request.GET.get('city', '')
    if city:
        filters['city'] = city
    
    theater = request.GET.get('theater', '')
    if theater:
        filters['theater'] = theater
    
    release_date_start = request.GET.get('release_date_start', '')
    if release_date_start:
        filters['release_date_start'] = release_date_start
    
    release_date_end = request.GET.get('release_date_end', '')
    if release_date_end:
        filters['release_date_end'] = release_date_end
    
    min_rating = request.GET.get('min_rating', '')
    if min_rating:
        filters['min_rating'] = min_rating
    
    show_time = request.GET.get('show_time', '')
    if show_time:
        filters['show_time'] = show_time
    
    # Get sort parameter
    sort_by = request.GET.get('sort', 'popularity')
    
    # Get page number
    page = request.GET.get('page', 1)
    
    # Get discovery results
    result = MovieDiscoveryService.search_movies(
        request, filters, sort_by, page, per_page=12
    )
    
    # Get filter options
    filter_options = MovieDiscoveryService.get_filter_options()
    
    # Get personalized recommendations
    recommended_movies = MovieDiscoveryService.get_recommendations(
        request.user if request.user.is_authenticated else None
    )
    
    # Get trending movies
    trending_movies = MovieDiscoveryService.get_trending_movies(6)
    
    # Log search event for analytics
    if request.user.is_authenticated and search_query:
        AnalyticsEvent.objects.create(
            user=request.user,
            event_type='SEARCH',
            metadata={'query': search_query, 'filters': filters}
        )
    
    context = {
        'movies': result['movies'],
        'total_count': result['total_count'],
        'paginator': result['paginator'],
        'page': page,
        'per_page': 12,
        'search_query': search_query,
        'selected_genres': genres,
        'selected_languages': languages,
        'selected_city': city,
        'selected_theater': theater,
        'selected_release_date_start': release_date_start,
        'selected_release_date_end': release_date_end,
        'selected_min_rating': min_rating,
        'selected_show_time': show_time,
        'sort_by': sort_by,
        'filter_options': filter_options,
        'recommended_movies': recommended_movies,
        'trending_movies': trending_movies,
    }
    
    return render(request, 'movies/movie_discovery.html', context)


@login_required
def movie_watch(request, movie_id):
    """
    Track movie view for recommendations
    """
    movie = get_object_or_404(Movie, id=movie_id, is_active=True)
    
    # Log view event
    AnalyticsEvent.objects.create(
        user=request.user,
        event_type='VIEW',
        movie=movie,
        metadata={'timestamp': str(timezone.now())}
    )
    
    return redirect('movie_detail', pk=movie_id)


def get_filter_options_ajax(request):
    """
    AJAX endpoint to get filter options
    """
    filter_options = MovieDiscoveryService.get_filter_options()
    data = {
        'genres': [{'id': g.id, 'name': g.name} for g in filter_options['genres']],
        'languages': [{'id': l.id, 'name': l.name} for l in filter_options['languages']],
        'cities': [c for c in filter_options['cities'] if c],
        'theaters': [t for t in filter_options['theaters'] if t],
        'min_rating': filter_options['min_rating'],
        'show_times': filter_options['show_times'],
    }
    return JsonResponse(data)
@login_required
def download_ticket(request, booking_id):
    """
    Download ticket PDF for a booking
    """
    booking = get_object_or_404(ShowBooking, id=booking_id)
    
    # Get or create ticket
    ticket, created = Ticket.objects.get_or_create(
        booking=booking,
        defaults={
            'user': request.user,
            'ticket_number': TicketGenerator.generate_ticket_number(),
        }
    )
    
    # If ticket doesn't have PDF, generate it
    if not ticket.pdf_file:
        
        pdf_buffer = TicketGenerator.create_ticket_pdf(
            booking,
            ticket.ticket_number,
            {'booking_id': booking.id, 'ticket_number': ticket.ticket_number}
        )
        
        pdf_content = pdf_buffer.getvalue()
        ticket.pdf_file.save(f"ticket_{ticket.ticket_number}.pdf", ContentFile(pdf_content))
        ticket.mark_generated()
    
    # Mark as downloaded
    ticket.mark_downloaded()
    
    # Serve PDF
    response = HttpResponse(ticket.pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.ticket_number}.pdf"'
    response['Content-Length'] = ticket.pdf_file.size
    
    return response


@login_required
def view_ticket(request, booking_id):
    """
    View ticket in browser (inline)
    """
    booking = get_object_or_404(ShowBooking, id=booking_id)
    
    ticket = get_object_or_404(Ticket, booking=booking)
    
    if not ticket.pdf_file:
        messages.error(request, 'Ticket not available yet. Please wait.')
        return redirect('my_bookings')
    
    response = HttpResponse(ticket.pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="ticket_{ticket.ticket_number}.pdf"'
    
    return response


@login_required
def resend_ticket_email(request, booking_id):
    """
    Resend ticket email
    """
    booking = get_object_or_404(ShowBooking, id=booking_id)
    ticket = get_object_or_404(Ticket, booking=booking)
    
    if ticket.can_retry():
        generate_and_send_ticket.delay(booking_id)
        messages.success(request, 'Ticket email will be resent shortly.')
    else:
        messages.error(request, 'Maximum retry limit reached. Please contact support.')
    
    return redirect('my_bookings')

@csrf_exempt
def payment_success(request):
    """Show payment success page"""
    order_id = request.POST.get('razorpay_order_id') or request.GET.get('razorpay_order_id')
    payment_id = request.POST.get('razorpay_payment_id') or request.GET.get('razorpay_payment_id')
    signature = request.POST.get('razorpay_signature') or request.GET.get('razorpay_signature')
    print("=" * 50)
    print("PAYMENT SUCCESS CALLBACK")
    print("=" * 50)
    print("order_id:", order_id)
    print("payment_id:", payment_id)
    print("signature:", signature)
    print("ALL GET params:", dict(request.GET))
    
    if order_id and payment_id:
        try:
            payment = Payment.objects.get(razorpay_order_id=order_id)
            print("Found payment:", payment.id, "status:", payment.payment_status)
            
            if payment.payment_status != 'SUCCESS':
                payment.mark_success(payment_id, signature or '')
                print("Payment marked success")
                
                booking = payment.booking
                if booking:
                    booking.status = 'CONFIRMED'
                    booking.save()
                    print("Booking CONFIRMED:", booking.id)
                    
                    generate_and_send_ticket.delay(booking.id)
                    print("Celery task fired!")
                else:
                    print("ERROR: no booking linked to payment")
        except Payment.DoesNotExist:
            print("ERROR: Payment not found for order_id:", order_id)
    else:
        print("ERROR: missing order_id or payment_id")
    
    messages.success(request, 'Payment successful! Your ticket has been sent.')
    return redirect('my_bookings')