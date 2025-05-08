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
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# Base URL for FastAPI
FASTAPI_URL = "http://127.0.0.1:8001"

# -------------------------------
# Premium Subscription Management
# -------------------------------

@shared_task
def remove_expired_premium_users():
    """
    Remove expired premium users and update their status.
    """
    expired_subs = PremiumSubscription.objects.filter(expires_at__lte=now())

    for sub in expired_subs:
        user = sub.user
        user.premium_status = False  
        user.save()
        sub.delete()

# -------------------------------
# Coupon Management
# -------------------------------

@shared_task
def generate_coupon_code():
    """
    Generates a random 6-character coupon code.
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@shared_task
def check_and_generate_coupons():
    """
    Removes expired coupons and generates new ones if none exist.
    """
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

# -------------------------------
# FastAPI Integration
# -------------------------------

@shared_task
def send_to_fastapi(model_path, image_path):
    """
    Send an image to FastAPI for inference.
    """
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

# -------------------------------
# Notification Management
# -------------------------------

@shared_task
def notify_user_task(user_id, message):
    """
    Create a notification for a user in the database.
    """
    from healthapp.models import Notification  # Import the Notification model

    try:
        Notification.objects.create(
            user_id=user_id,
            message=message,
            is_read=False,
            created_at=now()
        )
        return {"status": "success", "message": "Notification created successfully."}
    except Exception as e:
        return {"error": str(e)}

@shared_task
def notify_user_test(username, message):
    """
    Send a test notification to a WebSocket group.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "notifications",
        {
            "type": "send_notification",
            "message": f"{username}: {message}"
        }
    )

@shared_task
def send_email_task(subject, recipient_list, template_name, context, from_email="sasas1151@gmail.com"):
    """
    Sends an HTML email to the specified recipients.

    Args:
        subject (str): The subject of the email.
        recipient_list (list): A list of recipient email addresses.
        template_name (str): The name of the email template to render.
        context (dict): Context data for rendering the email template.
        from_email (str, optional): The sender's email address. Defaults to the default Django email setting.

    Returns:
        dict: A dictionary indicating success or failure.
    """
    try:
        # Render the HTML email template
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)  # Fallback to plain text

        # Send the email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=recipient_list,
            html_message=html_message,  # Send the HTML version
            fail_silently=False,
        )
        return {"status": "success", "message": "Email sent successfully."}
    except Exception as e:
        return {"error": str(e)}

# -------------------------------
# Doctor Synchronization
# -------------------------------

@shared_task
def sync_appointed_doctors(user_id):
    """
    Synchronize appointed doctors with FastAPI and notify the admin.
    """
    try:
        response = requests.get(f"{FASTAPI_URL}/approved-doctors")
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
                    "status": doc["status"],
                },
            )

        # Delete doctors no longer present in FastAPI
        AppointedDoctor.objects.exclude(external_id__in=fastapi_ids).delete()

        # Notify admin via WebSocket
        channel_layer = get_channel_layer()
        message = "Doctor sync completed successfully"
        async_to_sync(channel_layer.group_send)(
            f'notifications_{user_id}',
            {
                'type': 'send_notification',
                'message': message
            }
        )
        return {"status": "success", "data": "sync completed"}
    except Exception as e:
        # Notify admin of failure
        channel_layer = get_channel_layer()
        message = f"Doctor sync failed: {str(e)}"
        async_to_sync(channel_layer.group_send)(
            f'notifications_{user_id}',
            {
                'type': 'send_notification',
                'message': message
            }
        )
        return {"error": str(e)}