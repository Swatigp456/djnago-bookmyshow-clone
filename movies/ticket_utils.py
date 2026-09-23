# movies/ticket_utils.py
import os
import io
import qrcode
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import datetime
import random
import string
import qrcode
from io import BytesIO
import base64

class TicketGenerator:
    """Generate professional PDF tickets with QR codes"""
    
    @staticmethod
    def generate_ticket_number():
        """Generate unique ticket number"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"BMS-{timestamp}-{random_str}"
    
    @staticmethod
    def generate_qr_code(data):
        """Generate QR code for ticket"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr
    
    @staticmethod
    def create_ticket_pdf(booking, ticket_number, qr_code_data):
        """
        Create a professional PDF ticket
        
        Args:
            booking: ShowBooking object
            ticket_number: Unique ticket number
            qr_code_data: Data for QR code (booking ID or ticket number)
        
        Returns:
            BytesIO: PDF file in memory
        """
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            alignment=TA_CENTER,
            spaceAfter=20,
        )
        
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#0d47a1'),
            spaceBefore=10,
            spaceAfter=10,
        )
        
        normal_style = ParagraphStyle(
            'NormalStyle',
            parent=styles['Normal'],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#333333'),
        )
        
        value_style = ParagraphStyle(
            'ValueStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a237e'),
            fontName='Helvetica-Bold',
        )
        
        # Build story
        story = []
        
        # Header
        story.append(Paragraph("🎬 BookMySeat", title_style))
        story.append(Paragraph("Movie Ticket", header_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Ticket ID: <b>{ticket_number}</b>", normal_style))
        story.append(Paragraph(f"Booking Date: {booking.booking_date.strftime('%B %d, %Y at %I:%M %p')}", normal_style))
        story.append(Spacer(1, 15))
        
        # Divider line
        story.append(Table([['_' * 80]], colWidths=[180*mm], style=[
            ('LINEBELOW', (0, 0), (-1, -1), 2, colors.HexColor('#1a237e')),
        ]))
        story.append(Spacer(1, 15))
        
        # Movie Details
        story.append(Paragraph("🎥 Movie Details", header_style))
        movie_data = [
            ['Movie:', booking.show.movie.name],
            ['Genre:', booking.show.movie.genres or 'N/A'],
            ['Duration:', f"{booking.show.movie.duration} minutes" if booking.show.movie.duration else 'N/A'],
            ['Certification:', booking.show.movie.certification or 'N/A'],
        ]
        
        movie_table = Table(movie_data, colWidths=[60*mm, 100*mm])
        movie_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#0d47a1')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        story.append(movie_table)
        story.append(Spacer(1, 10))
        
        # Show Details
        story.append(Paragraph("🏛️ Show Details", header_style))
        show_data = [
            ['Theater:', booking.show.screen.theater.name],
            ['Screen:', f"Screen {booking.show.screen.screen_number}"],
            ['Date:', booking.show.show_date.strftime('%A, %B %d, %Y')],
            ['Time:', booking.show.show_time.strftime('%I:%M %p')],
            ['Seats:', booking.seats],
            ['Total Price:', f"₹{booking.total_price}"],
        ]
        
        show_table = Table(show_data, colWidths=[60*mm, 100*mm])
        show_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#0d47a1')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        story.append(show_table)
        story.append(Spacer(1, 15))
        
        # Divider line
        story.append(Table([['_' * 80]], colWidths=[180*mm], style=[
            ('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
        ]))
        story.append(Spacer(1, 10))
        
        # QR Code section
        qr_data = f"BMS-TICKET-{ticket_number}"
        qr_img = TicketGenerator.generate_qr_code(qr_data)
        
        # Create QR image for PDF
        qr_pil = Image.open(qr_img)
        qr_pil = qr_pil.resize((150, 150))
        qr_buffer = BytesIO()
        qr_pil.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        # QR Code with text
        qr_table_data = [
            [Paragraph("Scan QR Code for Verification", styles['Normal'])],
            [RLImage(qr_buffer, width=150, height=150)],
            [Paragraph(f"Ticket ID: {ticket_number}", normal_style)],
        ]
        
        qr_table = Table(qr_table_data, colWidths=[180*mm])
        qr_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(qr_table)
        
        # Footer
        story.append(Spacer(1, 20))
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
        )
        story.append(Paragraph("Thank you for choosing BookMySeat!", footer_style))
        story.append(Paragraph("Please present this ticket at the counter.", footer_style))
        story.append(Paragraph("© BookMySeat 2024", footer_style))
        
        # Build PDF
        doc.build(story)
        
        return buffer