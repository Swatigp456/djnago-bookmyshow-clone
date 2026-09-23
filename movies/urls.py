from django.urls import path
from . import views
from . import webhook_handler

urlpatterns = [
    # Movie URLs
    path('', views.movie_list, name='movie_list'),
    path('<int:pk>/', views.movie_detail, name='movie_detail'),
    path('trending/', views.trending_movies, name='trending_movies'),
    path('recent/', views.recent_movies, name='recent_movies'),
    
    # Theater URLs
    path('<int:movie_id>/theaters/', views.theater_list, name='theater_list'),
    
    # Genre URLs
    path('genres/', views.genre_list, name='genre_list'),
    path('genres/<int:pk>/', views.genre_detail, name='genre_detail'),
    
    # Language URLs
    path('languages/', views.language_list, name='language_list'),
    path('languages/<int:pk>/', views.language_detail, name='language_detail'),
    
    # Review URLs
    path('<int:movie_id>/review/add/', views.add_review, name='add_review'),
    path('review/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    path('review/<int:review_id>/report/', views.report_review, name='report_review'),
    
    # Booking URLs
    path('book/<int:show_id>/', views.book_ticket, name='book_ticket'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    
    # API URLs
    path('api/rating/<int:movie_id>/', views.get_movie_rating, name='get_movie_rating'),
    
    # Smart Seat Reservation URLs
    path('seat-selection/<int:show_id>/', views.seat_selection, name='seat_selection'),
    path('api/seat-availability/<int:show_id>/', views.get_seat_availability, name='seat_availability'),
    path('api/lock-seats/<int:show_id>/', views.lock_seats, name='lock_seats'),
    path('api/reserve-seats/<int:show_id>/', views.reserve_seats, name='reserve_seats'),
    path('api/confirm-reservation/<int:show_id>/', views.confirm_reservation, name='confirm_reservation'),
    path('api/release-seats/<int:show_id>/', views.release_seats, name='release_seats'),
    
    # Payment URLs
    path('payment/<int:booking_id>/', views.initiate_payment, name='initiate_payment'),
    path('payment/verify/', views.verify_payment, name='verify_payment'),
    path('payment/status/<int:payment_id>/', views.payment_status, name='payment_status'),
    path('payment/history/', views.payment_history, name='payment_history'),
    path('payment/retry/<int:booking_id>/', views.retry_payment, name='retry_payment'),
    path('payment/cancel/<int:payment_id>/', views.cancel_payment, name='cancel_payment'),
    
    # Webhook URL
    path('webhook/razorpay/', webhook_handler.razorpay_webhook, name='razorpay_webhook'),
    # Add these to your urlpatterns

# Movie Discovery URLs
   path('discover/', views.movie_discovery, name='movie_discovery'),
   path('api/filter-options/', views.get_filter_options_ajax, name='filter_options'),
   path('watch/<int:movie_id>/', views.movie_watch, name='movie_watch'),     
   path('ticket/download/<int:booking_id>/', views.download_ticket, name='download_ticket'),
   path('ticket/view/<int:booking_id>/', views.view_ticket, name='view_ticket'),
   path('ticket/resend/<int:booking_id>/', views.resend_ticket_email, name='resend_ticket_email'),  
   path('payment/success/', views.payment_success, name='payment_success'),         
]