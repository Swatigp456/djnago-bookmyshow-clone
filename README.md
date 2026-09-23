# BookMySeat

A Django-based movie ticket booking system with automated PDF ticket generation and asynchronous email delivery via Celery.

## Features

- Browse movies, theaters, and shows
- Seat selection with real-time availability
- Razorpay payment integration
- Automated PDF ticket with QR code
- Asynchronous email delivery (Celery + Redis)
- Download tickets from booking history
- Automatic retry on failed emails

## Setup

### 1. Install dependencies
pip install -r requirements.txt

### 2. Create `.env` file
SECRET_KEY=your_django_secret_key
RAZORPAY_KEY_ID=rzp_test_xxxxx
RAZORPAY_KEY_SECRET=xxxxx
RAZORPAY_WEBHOOK_SECRET=xxxxx
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password

### 3. Run migrations
python manage.py migrate

### 4. Start Redis
redis-server

### 5. Start Celery worker
celery -A bookmyseat worker --loglevel=info --pool=solo

### 6. Start Django
python manage.py runserver

Open http://127.0.0.1:8000/

## Task 6 — Automated Ticket Generation

After successful payment:
1. Booking status changes to CONFIRMED
2. Celery task `generate_and_send_ticket` fires asynchronously
3. PDF ticket with QR code is generated
4. Email with PDF attachment is sent to user
5. If email fails, it retries up to 3 times

Users can download tickets from `/my-bookings/`.
