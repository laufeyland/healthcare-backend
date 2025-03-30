from django.contrib.auth.models import AbstractUser
from django.db import models

# Enums for status fields
class Role(models.TextChoices):
    USER = 'user'
    PATIENT = 'patient'
    ADMIN = 'admin'

class AppointmentStatus(models.TextChoices):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    CANCELLED = 'cancelled'

class ReportStatus(models.TextChoices):
    PENDING = 'pending'
    REVIEWED = 'reviewed'
    COMPLETED = 'completed'

class AIModelStatus(models.TextChoices):
    TRAINING = 'training'
    DEPLOYED = 'deployed'
    ARCHIVED = 'archived'

# Custom User Model
class CustomUser(AbstractUser):
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=[('m', 'm'), ('f', 'f'), ('o', 'o')])
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    settings = models.JSONField(default=dict, blank=True)
    premium_status = models.BooleanField(default=False)
    def __str__(self):
        return self.username

# Appointment Model
class Appointment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateTimeField()
    status = models.CharField(max_length=10, choices=AppointmentStatus.choices, default=AppointmentStatus.PENDING)

# Medical History Model
class MedicalHistory(models.Model):
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='medical_histories')
    scan = models.ImageField(upload_to='scans/')
    ai_interpretation = models.TextField()
    record_date = models.DateTimeField(auto_now_add=True)

# Report Model
class Report(models.Model):
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reports')
    report_date = models.DateTimeField(auto_now_add=True)
    report_details = models.TextField()
    status = models.CharField(max_length=10, choices=ReportStatus.choices, default=ReportStatus.PENDING)

# AI Model
class AIModel(models.Model):
    model_name = models.CharField(max_length=255)
    version = models.CharField(max_length=50)
    status = models.CharField(max_length=10, choices=AIModelStatus.choices, default=AIModelStatus.TRAINING)
    parameters = models.JSONField(default=dict, blank=True)

# Premium Subscription Model
class PremiumSubscription(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='premium_subscription')
    premium_expiry = models.DateTimeField()

# Coupon Model
class Coupon(models.Model):
    coupon_code = models.CharField(max_length=50, unique=True)
    valid_until = models.DateTimeField()
    description = models.TextField(blank=True, null=True)
