from celery import shared_task, uuid
from django.utils.timezone import now, timedelta
from .models import *
import random
import string
from healthapp.models import Coupon
import random
import string
def generate_coupon_code(length=6):
    """Generate a random alphanumeric coupon code of the given length."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

@shared_task
def remove_expired_premium_users():
    """Remove expired premium users and update their status."""
    expired_subs = PremiumSubscription.objects.filter(expires_at__lte=now())

    for sub in expired_subs:
        user = sub.user
        user.premium_status = False  
        user.save()
        sub.delete()  

@shared_task

def generate_coupon_code():
    """Generates a random 6-character coupon code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@shared_task
def check_and_generate_coupons():
    """Removes expired coupons and generates new ones if none exist."""
    try:
        # Remove expired coupons
        Coupon.objects.filter(valid_until__lt=now()).delete()

        # Generate new coupons if none exist
        if not Coupon.objects.exists():
            new_coupons = [
                Coupon(
                    coupon_code=generate_coupon_code(),
                    valid_until=now() + timedelta(seconds=8),
                    description="Automatically added coupon"
                )
                for _ in range(10)
            ]
            Coupon.objects.bulk_create(new_coupons)

        return "Coupons checked and updated"
    except Exception as e:
        return f"Error: {str(e)}"
