# add_movies.py
import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookmyseat.settings')
django.setup()

from movies.models import Movie, Genre, Language, Theater, Screen, Show

# Create Genres
genres = ['Action', 'Drama', 'Comedy', 'Sci-Fi', 'Thriller', 'Romance']
for genre_name in genres:
    genre, created = Genre.objects.get_or_create(name=genre_name)
    if created:
        print(f"✅ Created genre: {genre_name}")

# Create Languages
languages = ['English', 'Hindi', 'Tamil', 'Telugu', 'Malayalam']
for lang_name in languages:
    lang, created = Language.objects.get_or_create(
        name=lang_name,
        defaults={'code': lang_name[:2].lower(), 'is_active': True}
    )
    if created:
        print(f"✅ Created language: {lang_name}")

# Create Movies
movies_data = [
    {
        'name': 'Avengers: Endgame',
        'rating': 4.8,
        'cast': 'Robert Downey Jr., Chris Evans, Scarlett Johansson',
        'description': 'The Avengers assemble to defeat Thanos in an epic battle to save the universe.',
        'is_active': True,
        'is_trending': True,
        'is_recent': True,
        'release_date': datetime.now().date() - timedelta(days=30),
        'duration': 181,
        'director': 'Anthony Russo',
        'certification': 'UA'
    },
    {
        'name': 'Inception',
        'rating': 4.9,
        'cast': 'Leonardo DiCaprio, Joseph Gordon-Levitt',
        'description': 'A thief who steals corporate secrets through dream-sharing technology.',
        'is_active': True,
        'is_trending': True,
        'is_recent': False,
        'release_date': datetime.now().date() - timedelta(days=100),
        'duration': 148,
        'director': 'Christopher Nolan',
        'certification': 'UA'
    },
    {
        'name': 'The Dark Knight',
        'rating': 4.8,
        'cast': 'Christian Bale, Heath Ledger, Aaron Eckhart',
        'description': 'When the menace known as the Joker wreaks havoc and chaos on the people of Gotham.',
        'is_active': True,
        'is_trending': False,
        'is_recent': False,
        'release_date': datetime.now().date() - timedelta(days=200),
        'duration': 152,
        'director': 'Christopher Nolan',
        'certification': 'A'
    },
    {
        'name': 'Interstellar',
        'rating': 4.7,
        'cast': 'Matthew McConaughey, Anne Hathaway',
        'description': "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival.",
        'is_active': True,
        'is_trending': True,
        'is_recent': True,
        'release_date': datetime.now().date() - timedelta(days=45),
        'duration': 169,
        'director': 'Christopher Nolan',
        'certification': 'UA'
    },
    {
        'name': 'The Shawshank Redemption',
        'rating': 4.9,
        'cast': 'Tim Robbins, Morgan Freeman',
        'description': 'Two imprisoned men bond over a number of years, finding solace and eventual redemption.',
        'is_active': True,
        'is_trending': False,
        'is_recent': False,
        'release_date': datetime.now().date() - timedelta(days=365),
        'duration': 142,
        'director': 'Frank Darabont',
        'certification': 'A'
    }
]

for movie_data in movies_data:
    movie, created = Movie.objects.get_or_create(
        name=movie_data['name'],
        defaults=movie_data
    )
    if created:
        print(f"✅ Created movie: {movie.name}")
    else:
        print(f"⏭️ Movie already exists: {movie.name}")

# Create Theater
theater, created = Theater.objects.get_or_create(
    name='PVR Cinemas',
    defaults={
        'movie': Movie.objects.first(),
        'time': datetime.now() + timedelta(days=1)
    }
)
if created:
    print(f"✅ Created theater: {theater.name}")

# Create Screen
screen, created = Screen.objects.get_or_create(
    theater=theater,
    screen_number=1,
    defaults={'capacity': 100, 'is_active': True}
)
if created:
    print(f"✅ Created screen: {screen}")

# Create Shows for each movie
for movie in Movie.objects.all():
    show_date = datetime.now().date() + timedelta(days=1)
    show_time = datetime.now().time().replace(hour=18, minute=0, second=0)
    
    show, created = Show.objects.get_or_create(
        movie=movie,
        screen=screen,
        show_date=show_date,
        show_time=show_time,
        defaults={
            'price': 250.00,
            'status': 'SCHEDULED',
            'is_active': True
        }
    )
    if created:
        print(f"✅ Created show for: {movie.name}")

print("\n✅ Data creation complete!")
print(f"📊 Movies: {Movie.objects.count()}")
print(f"🎭 Genres: {Genre.objects.count()}")
print(f"🌐 Languages: {Language.objects.count()}")
print(f"📅 Shows: {Show.objects.count()}")