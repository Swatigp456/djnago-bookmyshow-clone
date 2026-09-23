from django import forms
from .models import Review, ReviewReport, ShowBooking  # Changed from Booking to ShowBooking

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'review_text']
        widgets = {
            'review_text': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Write your review here...',
                'class': 'form-control'
            }),
            'rating': forms.Select(attrs={'class': 'form-select'})
        }
        labels = {
            'rating': 'Rating (1-5 Stars)',
            'review_text': 'Your Review'
        }

class ReviewReportForm(forms.ModelForm):
    REASON_CHOICES = [
        ('SPAM', 'Spam or Promotional Content'),
        ('OFFENSIVE', 'Offensive Language'),
        ('FAKE', 'Fake or Misleading'),
        ('COPYRIGHT', 'Copyright Infringement'),
        ('OTHER', 'Other'),
    ]
    
    reason = forms.ChoiceField(choices=REASON_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    
    class Meta:
        model = ReviewReport
        fields = ['reason', 'description']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Provide additional details...',
                'class': 'form-control'
            })
        }

class BookingForm(forms.ModelForm):
    class Meta:
        model = ShowBooking  # IMPORTANT: Use ShowBooking, not Booking
        fields = ['seats']
        widgets = {
            'seats': forms.NumberInput(attrs={
                'min': 1,
                'max': 10,
                'class': 'form-control',
                'value': 1
            })
        }
        labels = {
            'seats': 'Number of Seats'
        }
from django import forms
from .models import Review, ReviewReport, ShowBooking, SeatReservation

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'review_text']
        widgets = {
            'review_text': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Write your review here...',
                'class': 'form-control'
            }),
            'rating': forms.Select(attrs={'class': 'form-select'})
        }
        labels = {
            'rating': 'Rating (1-5 Stars)',
            'review_text': 'Your Review'
        }

class ReviewReportForm(forms.ModelForm):
    REASON_CHOICES = [
        ('SPAM', 'Spam or Promotional Content'),
        ('OFFENSIVE', 'Offensive Language'),
        ('FAKE', 'Fake or Misleading'),
        ('COPYRIGHT', 'Copyright Infringement'),
        ('OTHER', 'Other'),
    ]
    
    reason = forms.ChoiceField(choices=REASON_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    
    class Meta:
        model = ReviewReport
        fields = ['reason', 'description']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Provide additional details...',
                'class': 'form-control'
            })
        }

class BookingForm(forms.ModelForm):
    class Meta:
        model = ShowBooking
        fields = ['seats']
        widgets = {
            'seats': forms.NumberInput(attrs={
                'min': 1,
                'max': 10,
                'class': 'form-control',
                'value': 1
            })
        }
        labels = {
            'seats': 'Number of Seats'
        }

# ============================================
# NEW FORM FOR SMART SEAT RESERVATION
# ============================================

class SeatSelectionForm(forms.Form):
    """Form for selecting multiple seats"""
    seat_ids = forms.CharField(widget=forms.HiddenInput())
    
    def clean_seat_ids(self):
        data = self.cleaned_data['seat_ids']
        try:
            seat_ids = [int(x) for x in data.split(',') if x]
            if not seat_ids:
                raise forms.ValidationError("Please select at least one seat.")
            if len(seat_ids) > 10:
                raise forms.ValidationError("You can select maximum 10 seats.")
            return seat_ids
        except ValueError:
            raise forms.ValidationError("Invalid seat selection.")
# ============================================
# PAYMENT FORM - ADD TO movies/forms.py
# ============================================

class PaymentForm(forms.Form):
    """Payment form for Razorpay"""
    razorpay_order_id = forms.CharField(widget=forms.HiddenInput(), required=False)
    razorpay_payment_id = forms.CharField(widget=forms.HiddenInput(), required=False)
    razorpay_signature = forms.CharField(widget=forms.HiddenInput(), required=False)                