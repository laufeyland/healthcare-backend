from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.timezone import now, timedelta
from datetime import datetime
import os
from uuid import uuid4
# Enums for status fields
class Role(models.TextChoices):
    USER = 'user'
    PATIENT = 'patient'
    ADMIN = 'admin'

class AppointmentStatus(models.TextChoices):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    CANCELLED = 'cancelled'
    MISSED = 'missed'
    FINISHED = 'finished'
    COMPLETED = 'completed'

class TicketStatus(models.TextChoices):
    OPEN = 'open'
    REVIEWED = 'reviewed'
    CLOSED = 'closed'

class AIModelStatus(models.TextChoices):
    DEPLOYED = 'deployed'
    ARCHIVED = 'archived'

class NotificationType(models.TextChoices):
    APPOINTMENT = 'appointment'
    AI_RESULT = 'ai_result'
    MESSAGE = 'message'
    GENERAL = 'general'

class PaymentMethod(models.TextChoices):
    BARIDIMOB= 'baridimob',
    CIB = 'cib',
    CASH = 'cash',

# Custom User Model
class CustomUser(AbstractUser):
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=[('m', 'm'), ('f', 'f'), ('o', 'o')])
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    settings = models.JSONField(default=dict, blank=True)
    premium_status = models.BooleanField(default=False)
    ai_tries = models.PositiveIntegerField(default=0)
    def __str__(self):
        return self.username

# Appointment Model
class Appointment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateTimeField()
    reference = models.CharField(max_length=10, unique=True, blank=True, null=True)
    status = models.CharField(max_length=10, choices=AppointmentStatus.choices, default=AppointmentStatus.PENDING)

def user_scan_upload_path(instance, filename):
    date_path = datetime.now().strftime('%Y/%m/%d')
    
    # Generate a unique filename using a UUID to avoid collisions
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    
    # Organize by user ID and date
    return os.path.join("scans", str(instance.user.id), date_path, filename)

# Medical History Model
class MedicalHistory(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='medical_histories')
    scan = models.ImageField(upload_to=user_scan_upload_path)
    ai_interpretation = models.JSONField(default=dict, blank=True)
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True)
    record_date = models.DateTimeField(auto_now_add=True)

# Report Model
class Ticket(models.Model):

    subject = models.CharField(max_length=255)
    description = models.TextField()
    reported_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=TicketStatus, default=TicketStatus.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} ({self.status})"


# AI Model
class AIModel(models.Model):
    model_name = models.CharField(max_length=255)
    model_file = models.FileField(upload_to='models/')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=AIModelStatus.choices, default=AIModelStatus.DEPLOYED)
    parameters = models.JSONField(default=dict, blank=True)

# Premium Subscription Model
def default_expiry():
    return now() + timedelta(days=30)

class PremiumSubscription(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    expires_at = models.DateTimeField(default=default_expiry)  # Use a named function

    def has_expired(self):
        return now() >= self.expires_at

# Coupon Model
def default_coupon_expiry():
    return now() + timedelta(days=7)
class Coupon(models.Model):
    coupon_code = models.CharField(max_length=6, unique=True)
    valid_until = models.DateTimeField(default=default_coupon_expiry)
    description = models.TextField(blank=True, null=True)

    def has_expired(self):
        return now() >= self.expires_at

# Notification Model
class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.GENERAL)

    class Meta:
        ordering = ['-created_at']

# Payment Model
class Payment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    transaction_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=[('completed', 'completed'), ('failed', 'failed')], default='completed')

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.status}"