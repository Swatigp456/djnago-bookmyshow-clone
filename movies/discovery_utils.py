# movies/discovery_utils.py
from django.db.models import Q, Count, Avg, Sum, Min, Max
from django.db.models.functions import TruncDate
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Movie, Show, ShowBooking, AnalyticsEvent


class MovieDiscoveryService:
    """Service for movie discovery with search, filters, and recommendations"""
    
    @staticmethod
    def search_movies(request, filters=None, sort_by=None, page=1, per_page=12):
        """
        Search movies with filters and sorting
        """
        movies = Movie.objects.filter(is_active=True)
        
        # Search by title
        search_query = filters.get('search', '') if filters else ''
        if search_query:
            movies = movies.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(director__icontains=search_query) |
                Q(cast__icontains=search_query)
            )
        
        # Filter by genre (if you add genre field to Movie)
        genre_ids = filters.get('genres', []) if filters else []
        # Commenting out since Movie doesn't have genres field
        # if genre_ids:
        #     movies = movies.filter(genres__id__in=genre_ids)
        
        # Filter by language (if you add language field to Movie)
        language_ids = filters.get('languages', []) if filters else []
        # Commenting out since Movie doesn't have languages field
        # if language_ids:
        #     movies = movies.filter(languages__id__in=language_ids)
        
        # Filter by city
        city = filters.get('city', '') if filters else ''
        if city:
            movies = movies.filter(city__icontains=city)
        
        # Filter by theater
        theater = filters.get('theater', '') if filters else ''
        if theater:
            movies = movies.filter(theater__icontains=theater)
        
        # Filter by release date
        release_date_start = filters.get('release_date_start', '') if filters else ''
        release_date_end = filters.get('release_date_end', '') if filters else ''
        if release_date_start:
            movies = movies.filter(release_date__gte=release_date_start)
        if release_date_end:
            movies = movies.filter(release_date__lte=release_date_end)
        
        # Filter by rating
        min_rating = filters.get('min_rating', '') if filters else ''
        if min_rating:
            try:
                min_rating = float(min_rating)
                movies = movies.filter(rating__gte=min_rating)
            except ValueError:
                pass
        
        # Filter by show timings
        show_time = filters.get('show_time', '') if filters else ''
        if show_time:
            try:
                time_obj = datetime.strptime(show_time, '%H:%M').time()
                movies = movies.filter(shows__show_time__gte=time_obj).distinct()
            except ValueError:
                pass
        
        # Sort results
        if sort_by:
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
        else:
            movies = movies.order_by('-id')
        
        # Count total matching movies
        total_count = movies.count()
        
        # Paginate
        paginator = Paginator(movies, per_page)
        try:
            movies_page = paginator.page(page)
        except PageNotAnInteger:
            movies_page = paginator.page(1)
        except EmptyPage:
            movies_page = paginator.page(paginator.num_pages)
        
        return {
            'movies': movies_page,
            'total_count': total_count,
            'paginator': paginator,
            'page': page,
            'per_page': per_page,
        }
    
    @staticmethod
    def get_filter_options():
        """
        Get available filter options
        """
        return {
            'genres': [],  # No genres since Movie doesn't have genre field
            'languages': [],  # No languages since Movie doesn't have language field
            'cities': Movie.objects.filter(is_active=True).values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city=''),
            'theaters': Movie.objects.filter(is_active=True).values_list('theater', flat=True).distinct().exclude(theater__isnull=True).exclude(theater=''),
            'min_rating': [1, 2, 3, 4, 4.5],
            'show_times': ['10:00', '13:00', '18:00', '21:00'],
        }
    
    @staticmethod
    def get_recommendations(user, limit=6):
        """
        Get personalized movie recommendations for user
        """
        if not user or not user.is_authenticated:
            return Movie.objects.filter(is_active=True).order_by('-rating')[:limit]
        
        # Get user's booking history
        booked_movies = ShowBooking.objects.filter(
            user=user,
            status='CONFIRMED'
        ).values_list('show__movie__id', flat=True).distinct()
        
        # Get user's viewed movies
        viewed_movies = AnalyticsEvent.objects.filter(
            user=user,
            event_type='VIEW'
        ).values_list('movie__id', flat=True).distinct()
        
        # Get movies user has watched
        watched_movies = list(booked_movies) + list(viewed_movies)
        
        if watched_movies:
            # Get movies with similar directors or cast
            # Get directors of watched movies
            watched_directors = Movie.objects.filter(
                id__in=watched_movies
            ).values_list('director', flat=True).distinct()
            
            # Get cast of watched movies
            watched_cast = Movie.objects.filter(
                id__in=watched_movies
            ).values_list('cast', flat=True).distinct()
            
            # Get recommendations based on similar director or cast
            recommendations = Movie.objects.filter(
                is_active=True
            ).exclude(
                id__in=watched_movies
            ).filter(
                Q(director__in=watched_directors) |
                Q(cast__icontains=watched_cast[0] if watched_cast else '')
            ).order_by('-rating')[:limit]
            
            if recommendations.count() < limit:
                # Fallback: return top rated movies
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
            # Fallback: return top rated movies
            return Movie.objects.filter(
                is_active=True
            ).order_by('-rating')[:limit]
    
    @staticmethod
    def get_trending_movies(limit=10):
        """
        Get trending movies based on bookings and views
        """
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        trending = Movie.objects.filter(
            is_active=True,
            shows__bookings__booking_date__gte=thirty_days_ago,
            shows__bookings__status='CONFIRMED'
        ).annotate(
            popularity=Count('shows__bookings')
        ).order_by('-popularity')[:limit]
        
        if trending.count() < limit:
            # Fallback: return top rated movies
            extra_needed = limit - trending.count()
            extra = Movie.objects.filter(
                is_active=True
            ).exclude(
                id__in=trending.values_list('id', flat=True)
            ).order_by('-rating')[:extra_needed]
            trending = list(trending) + list(extra)
        
        return trending