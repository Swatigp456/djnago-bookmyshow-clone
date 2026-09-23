# movies/webhook_handler.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.conf import settings
import json
import hmac
import hashlib

from .models import Payment, ShowBooking, Seat


def verify_webhook_signature(payload, signature, secret):
    """
    Verify webhook signature
    """
    try:
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """
    Handle Razorpay webhook events
    """
    # Verify webhook signature
    payload = request.body
    signature = request.headers.get('X-Razorpay-Signature')
    
    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
    
    if not verify_webhook_signature(payload, signature, webhook_secret):
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    try:
        data = json.loads(payload)
        event = data.get('event')
        payload_data = data.get('payload', {})
        
        if event == 'payment.captured':
            # Payment successful
            payment_data = payload_data.get('payment', {}).get('entity', {})
            order_id = payment_data.get('order_id')
            payment_id = payment_data.get('id')
            
            payment = Payment.objects.filter(razorpay_order_id=order_id).first()
            if payment and payment.payment_status != 'SUCCESS':
                payment.mark_success(payment_id, 'webhook_verified')
                
                # Confirm booking
                if payment.booking:
                    payment.booking.status = 'CONFIRMED'
                    payment.booking.save()
                
                # Mark webhook processed
                payment.webhook_processed = True
                payment.webhook_processed_at = timezone.now()
                payment.save()
                
        elif event == 'payment.failed':
            # Payment failed
            payment_data = payload_data.get('payment', {}).get('entity', {})
            order_id = payment_data.get('order_id')
            error_description = payment_data.get('error_description', 'Payment failed')
            error_code = payment_data.get('error_code', 'FAILED')
            
            payment = Payment.objects.filter(razorpay_order_id=order_id).first()
            if payment and payment.payment_status != 'SUCCESS':
                payment.mark_failed(reason=error_description, code=error_code)
                
                # Release seats
                if payment.booking:
                    payment.booking.status = 'CANCELLED'
                    payment.booking.save()
                
        elif event == 'payment.refunded':
            # Payment refunded
            payment_data = payload_data.get('payment', {}).get('entity', {})
            payment_id = payment_data.get('id')
            
            payment = Payment.objects.filter(razorpay_payment_id=payment_id).first()
            if payment:
                payment.payment_status = 'REFUNDED'
                payment.save()
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)