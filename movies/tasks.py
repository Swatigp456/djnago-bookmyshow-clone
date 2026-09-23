# movies/tasks.py
from celery import shared_task
from django.core.mail import EmailMessage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings
from io import BytesIO
import logging

from .models import ShowBooking, Ticket
from .ticket_utils import TicketGenerator

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_and_send_ticket(self, booking_id):
    """
    Generate ticket PDF and send email asynchronously
    """
    try:
        booking = ShowBooking.objects.get(id=booking_id)
        user = booking.user
        
        # Check if ticket already exists
        ticket, created = Ticket.objects.get_or_create(
            booking=booking,
            defaults={
                'user': user,
                'ticket_number': TicketGenerator.generate_ticket_number(),
            }
        )
        
        if not created and ticket.status == 'EMAIL_SENT':
            logger.info(f"Ticket {ticket.ticket_number} already sent for booking {booking_id}")
            return {'status': 'already_sent', 'ticket_id': ticket.ticket_number}
        
        # Generate QR code and PDF
        ticket_number = ticket.ticket_number if created else ticket.ticket_number
        
        # Generate PDF
        pdf_buffer = TicketGenerator.create_ticket_pdf(
            booking, 
            ticket_number,
            {'booking_id': booking.id, 'ticket_number': ticket_number}
        )
        
        # Save PDF to ticket
        pdf_content = pdf_buffer.getvalue()
        if not created:
            ticket.pdf_file.save(f"ticket_{ticket_number}.pdf", ContentFile(pdf_content))
        
        ticket.mark_generated()
        
        # Send email with PDF attachment
        subject = f"Your BookMySeat Ticket - {booking.show.movie.name}"
        message = f"""
        Dear {user.username},
        
        Thank you for booking with BookMySeat!
        
        Ticket Details:
        Movie: {booking.show.movie.name}
        Theater: {booking.show.screen.theater.name}
        Date: {booking.show.show_date.strftime('%B %d, %Y')}
        Time: {booking.show.show_time.strftime('%I:%M %p')}
        Seats: {booking.seats}
        Total: ₹{booking.total_price}
        Ticket ID: {ticket_number}
        
        Please find your ticket attached.
        
        Important Notes:
        - Please arrive 15 minutes before the show
        - Carry a valid ID proof
        - This ticket is non-transferable
        
        Thank you for choosing BookMySeat!
        """
        
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
            reply_to=[settings.DEFAULT_FROM_EMAIL],
        )
        
        # Attach PDF
        email.attach(f"ticket_{ticket_number}.pdf", pdf_content, 'application/pdf')
        
        # Send email
        email.send()
        
        # Update ticket status
        ticket.mark_email_sent()
        
        logger.info(f"Ticket {ticket_number} sent to {user.email}")
        
        return {
            'status': 'success',
            'ticket_id': ticket_number,
            'email': user.email,
            'booking_id': booking_id
        }
        
    except Exception as e:
        logger.error(f"Error generating ticket for booking {booking_id}: {str(e)}")
        
        # Update ticket status if exists
        try:
            ticket = Ticket.objects.get(booking_id=booking_id)
            ticket.mark_email_failed(str(e))
        except Ticket.DoesNotExist:
            pass
        
        # Retry the task
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task
def retry_failed_tickets():
    """
    Retry failed ticket emails
    """
    from .models import Ticket
    
    failed_tickets = Ticket.objects.filter(
        status='EMAIL_FAILED',
        retry_count__lt=3
    )
    
    retried = 0
    for ticket in failed_tickets:
        generate_and_send_ticket.delay(ticket.booking.id)
        retried += 1
    
    return {'retried': retried}


@shared_task
def cleanup_old_tickets(days=30):
    """
    Clean up old tickets (optional)
    """
    from .models import Ticket
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    old_tickets = Ticket.objects.filter(generated_at__lt=cutoff_date)
    
    # Delete old tickets (or archive them)
    count = old_tickets.delete()[0]
    
    return {'deleted': count}