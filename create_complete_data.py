# create_complete_data.py
import os
import django
from datetime import datetime, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')
django.setup()

from movies.models import Movie, Theater, Screen, Seat, Show, ShowBooking, Payment
from django.contrib.auth.models import User

print("=" * 70)
print("🎬 CREATING COMPLETE MOVIE DATA WITH SHOWS & SEATS")
print("=" * 70)

# ============================================
# 1. CREATE MOVIES (if none exist)
# ============================================
movies_data = [
    {
        'name': 'Avengers: Endgame',
        'rating': 4.8,
        'cast': 'Robert Downey Jr., Chris Evans, Scarlett Johansson',
        'description': 'The Avengers assemble to defeat Thanos in an epic battle.',
        'director': 'Anthony Russo',
        'duration': 181,
        'release_date': datetime(2019, 4, 26).date(),
        'certification': 'UA',
        'city': 'Mumbai',
        'theater': 'PVR Cinemas',
        'is_trending': True,
        'is_recent': False,
    },
    {
        'name': 'Inception',
        'rating': 4.9,
        'cast': 'Leonardo DiCaprio, Joseph Gordon-Levitt',
        'description': 'A thief who steals corporate secrets through dream-sharing technology.',
        'director': 'Christopher Nolan',
        'duration': 148,
        'release_date': datetime(2010, 7, 16).date(),
        'certification': 'UA',
        'city': 'Delhi',
        'theater': 'INOX Leisure',
        'is_trending': True,
        'is_recent': False,
    },
    {
        'name': 'The Dark Knight',
        'rating': 4.8,
        'cast': 'Christian Bale, Heath Ledger',
        'description': 'When the menace known as the Joker wreaks havoc on Gotham.',
        'director': 'Christopher Nolan',
        'duration': 152,
        'release_date': datetime(2008, 7, 18).date(),
        'certification': 'A',
        'city': 'Bangalore',
        'theater': 'PVR Cinemas',
        'is_trending': True,
        'is_recent': False,
    },
    {
        'name': 'Interstellar',
        'rating': 4.7,
        'cast': 'Matthew McConaughey, Anne Hathaway',
        'description': "A team of explorers travel through a wormhole in space.",
        'director': 'Christopher Nolan',
        'duration': 169,
        'release_date': datetime(2014, 11, 7).date(),
        'certification': 'UA',
        'city': 'Hyderabad',
        'theater': 'Cinepolis',
        'is_trending': True,
        'is_recent': False,
    },
    {
        'name': 'Oppenheimer',
        'rating': 4.7,
        'cast': 'Cillian Murphy, Emily Blunt',
        'description': 'The story of J. Robert Oppenheimer and the atomic bomb.',
        'director': 'Christopher Nolan',
        'duration': 180,
        'release_date': datetime(2023, 7, 21).date(),
        'certification': 'A',
        'city': 'Mumbai',
        'theater': 'AMC Multiplex',
        'is_trending': True,
        'is_recent': True,
    },
    {
        'name': 'Barbie',
        'rating': 4.5,
        'cast': 'Margot Robbie, Ryan Gosling',
        'description': 'Barbie and Ken discover the real world.',
        'director': 'Greta Gerwig',
        'duration': 114,
        'release_date': datetime(2023, 7, 21).date(),
        'certification': 'UA',
        'city': 'Chennai',
        'theater': 'Carnival Cinemas',
        'is_trending': True,
        'is_recent': True,
    },
    {
        'name': 'Dune: Part Two',
        'rating': 4.6,
        'cast': 'Timothée Chalamet, Zendaya',
        'description': 'Paul Atreides continues his journey on Arrakis.',
        'director': 'Denis Villeneuve',
        'duration': 166,
        'release_date': datetime(2024, 3, 1).date(),
        'certification': 'UA',
        'city': 'Delhi',
        'theater': 'INOX Leisure',
        'is_trending': True,
        'is_recent': True,
    },
]

print("\n🎬 Creating movies...")
created_movies = []
for data in movies_data:
    movie, created = Movie.objects.get_or_create(
        name=data['name'],
        defaults={
            'rating': data['rating'],
            'cast': data['cast'],
            'description': data['description'],
            'director': data['director'],
            'duration': data['duration'],
            'release_date': data['release_date'],
            'certification': data['certification'],
            'city': data['city'],
            'theater': data['theater'],
            'is_active': True,
            'is_trending': data.get('is_trending', False),
            'is_recent': data.get('is_recent', False),
        }
    )
    created_movies.append(movie)
    print(f"   {'✅ Created' if created else '✅ Found'}: {movie.name}")

# ============================================
# 2. CREATE THEATERS
# ============================================
print("\n🏛️ Creating theaters...")

theater_data = [
    {'name': 'PVR Cinemas', 'city': 'Mumbai', 'screens': 3},
    {'name': 'INOX Leisure', 'city': 'Delhi', 'screens': 3},
    {'name': 'Cinepolis', 'city': 'Bangalore', 'screens': 3},
    {'name': 'AMC Multiplex', 'city': 'Hyderabad', 'screens': 2},
    {'name': 'Carnival Cinemas', 'city': 'Chennai', 'screens': 2},
]

theaters = []
for data in theater_data:
    theater, created = Theater.objects.get_or_create(
        name=data['name'],
        defaults={
            'movie': created_movies[0],
            'time': datetime.now() + timedelta(days=1)
        }
    )
    theaters.append(theater)
    print(f"   {'✅ Created' if created else '✅ Found'}: {theater.name}")

# ============================================
# 3. CREATE SCREENS
# ============================================
print("\n📺 Creating screens...")

screens = []
for theater in theaters:
    # Get number of screens for this theater
    num_screens = 3 if 'PVR' in theater.name or 'INOX' in theater.name else 2
    
    for i in range(1, num_screens + 1):
        screen, created = Screen.objects.get_or_create(
            theater=theater,
            screen_number=i,
            defaults={
                'capacity': random.choice([80, 100, 120, 150]),
                'is_active': True
            }
        )
        screens.append(screen)
        print(f"   {'✅ Created' if created else '✅ Found'}: {theater.name} - Screen {i}")

# ============================================
# 4. CREATE SEATS (MOST IMPORTANT!)
# ============================================
print("\n🪑 Creating seats...")

rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
total_seats_created = 0

for screen in screens:
    # Delete existing seats for this screen
    Seat.objects.filter(theater=screen.theater, screen=screen).delete()
    
    # Create new seats
    seats_created = 0
    for row in rows[:5]:  # A-E rows (50 seats)
        for num in range(1, 11):
            seat_number = f"{row}{num}"
            Seat.objects.create(
                theater=screen.theater,
                screen=screen,
                seat_number=seat_number,
                is_booked=False
            )
            seats_created += 1
    
    total_seats_created += seats_created
    print(f"   ✅ Created {seats_created} seats for {screen.theater.name} - Screen {screen.screen_number}")

print(f"   📊 Total seats created: {total_seats_created}")

# ============================================
# 5. CREATE SHOWS (VERY IMPORTANT!)
# ============================================
print("\n📅 Creating shows...")

# Show timings
morning_slots = ['09:00', '10:00', '11:00']
afternoon_slots = ['12:00', '13:00', '14:00', '15:00']
evening_slots = ['16:00', '17:00', '18:00', '19:00']
night_slots = ['20:00', '21:00', '22:00']

all_slots = morning_slots + afternoon_slots + evening_slots + night_slots
prices_by_time = {
    'morning': [150, 180, 200],
    'afternoon': [180, 200, 220],
    'evening': [220, 250, 280],
    'night': [250, 280, 300]
}

total_shows_created = 0

for movie in created_movies:
    print(f"\n   🎬 {movie.name}")
    
    # Select random theaters for this movie (2-3 theaters)
    selected_theaters = random.sample(theaters, min(random.randint(2, 3), len(theaters)))
    
    for theater in selected_theaters:
        # Get screens for this theater
        theater_screens = Screen.objects.filter(theater=theater, is_active=True)
        
        for screen in theater_screens:
            # Create shows for next 5 days
            for day_offset in range(1, 6):  # 5 days
                show_date = datetime.now().date() + timedelta(days=day_offset)
                
                # Select 2-3 random show times per day
                num_shows = random.randint(2, 3)
                selected_times = random.sample(all_slots, num_shows)
                
                for time_str in selected_times:
                    hour, minute = map(int, time_str.split(':'))
                    show_time = datetime.now().time().replace(hour=hour, minute=minute)
                    
                    # Determine price based on time
                    if hour < 12:
                        price = random.choice(prices_by_time['morning'])
                    elif hour < 16:
                        price = random.choice(prices_by_time['afternoon'])
                    elif hour < 20:
                        price = random.choice(prices_by_time['evening'])
                    else:
                        price = random.choice(prices_by_time['night'])
                    
                    show, created = Show.objects.get_or_create(
                        movie=movie,
                        screen=screen,
                        show_date=show_date,
                        show_time=show_time,
                        defaults={
                            'price': price,
                            'status': 'SCHEDULED',
                            'is_active': True
                        }
                    )
                    if created:
                        total_shows_created += 1

print(f"\n   ✅ Total shows created: {total_shows_created}")

# ============================================
# 6. CREATE USERS & BOOKINGS (Optional)
# ============================================
print("\n👥 Creating users...")

users = []
user_names = ['raj', 'priya', 'amit', 'sneha', 'vikram', 'ananya', 'rahul', 'neha']

for name in user_names:
    user, created = User.objects.get_or_create(
        username=name,
        defaults={
            'email': f'{name}@example.com',
            'is_active': True
        }
    )
    if created:
        user.set_password('password123')
        user.save()
        users.append(user)

# Create admin
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("   ✅ Created admin user (admin/admin123)")

print(f"   ✅ Created {len(users)} regular users")

# Create some bookings
print("\n🎟️ Creating sample bookings...")
bookings_created = 0
all_shows = Show.objects.filter(is_active=True)

for user in users[:5]:
    for _ in range(random.randint(2, 5)):
        show = random.choice(all_shows)
        if not show:
            continue
        
        seats = random.randint(1, 3)
        total_price = show.price * seats
        booking_date = datetime.now() - timedelta(days=random.randint(0, 10))
        
        booking, created = ShowBooking.objects.get_or_create(
            user=user,
            show=show,
            booking_date=booking_date,
            defaults={
                'seats': seats,
                'total_price': total_price,
                'status': 'CONFIRMED'
            }
        )
        if created:
            bookings_created += 1

print(f"   ✅ Created {bookings_created} sample bookings")

# ============================================
# 7. SUMMARY
# ============================================
print("\n" + "=" * 70)
print("✅ DATA CREATION COMPLETE!")
print("=" * 70)

print(f"\n📊 Summary:")
print(f"   🎬 Movies: {Movie.objects.filter(is_active=True).count()}")
print(f"   🏛️ Theaters: {Theater.objects.count()}")
print(f"   📺 Screens: {Screen.objects.count()}")
print(f"   🪑 Seats: {Seat.objects.count()}")
print(f"   📅 Shows: {Show.objects.filter(is_active=True).count()}")
print(f"   👥 Users: {User.objects.count()}")
print(f"   🎟️ Bookings: {ShowBooking.objects.count()}")

print("\n📋 Movie-wise Shows:")
for movie in created_movies:
    show_count = Show.objects.filter(movie=movie, is_active=True).count()
    print(f"   🎬 {movie.name}: {show_count} shows")

print("\n🎯 Sample Shows:")
shows = Show.objects.filter(is_active=True).order_by('show_date', 'show_time')[:10]
for show in shows:
    print(f"   📅 {show.show_date.strftime('%b %d')} {show.show_time.strftime('%H:%M')} - {show.movie.name} - ₹{show.price} - {show.screen.theater.name}")

print("\n🔗 Test URLs:")
print(f"   Movies: http://127.0.0.1:8000/movies/")
movie = Movie.objects.first()
if movie:
    print(f"   Theater List: http://127.0.0.1:8000/movies/{movie.id}/theaters/")
    print(f"   Book Ticket: http://127.0.0.1:8000/movies/book/{Show.objects.first().id}/")
print(f"   Admin: http://127.0.0.1:8000/admin/")

print("\n👤 Admin Credentials:")
print(f"   Username: admin")
print(f"   Password: admin123")

print("\n👥 User Credentials (password123):")
for user in users[:5]:
    print(f"   {user.username}")

print("\n" + "=" * 70)
print("🎬 Your BookMyShow Clone is ready!")
print("=" * 70)