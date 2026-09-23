# movies/payment_utils.py
import razorpay
from django.conf import settings

class RazorpayClient:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        self.key_id = settings.RAZORPAY_KEY_ID
    
    def create_order(self, amount, currency="INR", receipt=None, notes=None):
        try:
            data = {
                "amount": int(amount * 100),
                "currency": currency,
                "receipt": receipt or f"order_{int(time.time())}",
                "payment_capture": 0
            }
            if notes:
                data["notes"] = notes
            
            order = self.client.order.create(data=data)
            return {
                'success': True,
                'order_id': order['id'],
                'amount': order['amount'],
                'currency': order['currency']
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_payment(self, order_id, payment_id, signature):
        try:
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            self.client.utility.verify_payment_signature(params_dict)
            return {'success': True, 'verified': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def capture_payment(self, payment_id, amount):
        try:
            payment = self.client.payment.capture(payment_id, int(amount * 100))
            return {'success': True, 'payment': payment}
        except Exception as e:
            return {'success': False, 'error': str(e)}