from celery import shared_task
from django.utils.timezone import now, timedelta
from .models import *
import random
import string
from healthapp.models import Coupon
import requests
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

FASTAPI_URL = "http://127.0.0.1:8001"

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
                    valid_until=now() + timedelta(days=7),
                    description="Automatically added coupon"
                )
                for _ in range(10)
            ]
            Coupon.objects.bulk_create(new_coupons)

        return "Coupons checked and updated"
    except Exception as e:
        return f"Error: {str(e)}"

@shared_task
def send_to_fastapi(model_path, image_path):
    """Send an image to FastAPI for inference"""
    with open(image_path, "rb") as file:
        response = requests.post(
        f"{FASTAPI_URL}/infer",
        params={"model_path": model_path},
        files={"file": file}
    )
    try:
        result = response.json()
    except ValueError:
        return {"error": "Invalid response from inference API."}
    return result

@shared_task
def notify_user_task(user_id, message):
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "send_notification",
                "data": {
                    "message": message
                }
            }
        )
    except Exception as e:
        # Optional logging or retries
        print(f"[Celery] Failed to send WebSocket message to user {user_id}: {e}")

@shared_task
def notify_user_test(username, message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "notifications",
        {
            "type": "send_notification",
            "message": f"{username}: {message}"
        }
    )

@shared_task
def sync_appointed_doctors(user_id):
    try:
        response = requests.get(f"{FASTAPI_URL}/approved-doctors")  # adjust if needed
        response.raise_for_status()
        doctors = response.json()
    
        fastapi_ids = set()
        for doc in doctors:
            external_id = doc["external_id"]
            fastapi_ids.add(external_id)

            AppointedDoctor.objects.update_or_create(
                external_id=external_id,
                defaults={
                    "first_name": doc["first_name"],
                    "last_name": doc["last_name"],
                    "specialty": doc["specialty"],
                    "wilaya": doc["wilaya"],
                    "license_number": doc["license_number"],
                    "phone_number": doc["phone_number"],
                    "address": doc["address"],
                    "email": doc["email"],
                },
            )

        # Delete doctors no longer present in FastAPI
        AppointedDoctor.objects.exclude(external_id__in=fastapi_ids).delete()
        channel_layer = get_channel_layer()

        # Create a message to notify the admin
        message = "Doctor sync completed successfully"
    
        # Send the notification to the WebSocket group for that user
        channel_layer.group_send(
        f'notifications_{user_id}',  # The group name based on user ID
        {
            'type': 'send_notification',
            'message': message
        })
        return {"status": "success", "data": "sync completed"}
    except Exception as e:
        channel_layer = get_channel_layer()
        # Create a message to notify the admin
        message = f"Doctor sync failed: {str(e)}"
        channel_layer.group_send(
            f'notifications_{user_id}',  # The group name based on user ID
            {
                'type': 'send_notification',
                'message': message
            })
        return {"error": str(e)}