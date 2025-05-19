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

class DoctorStatus(models.TextChoices):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'

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
    VIP = 'vip'
    ARCHIVED = 'archived'

class NotificationType(models.TextChoices):
    APPOINTMENT = 'appointment'
    AI_RESULT = 'ai_result'
    MESSAGE = 'message'
    GENERAL = 'general'

class SpecialtyChoices(models.TextChoices):
    CARDIOLOGY = "Cardiology", "Cardiology"
    NEUROLOGY = "Neurology", "Neurology"
    RADIOLOGY = "Radiology", "Radiology"
    ONCOLOGY = "Oncology", "Oncology"
    DERMATOLOGY = "Dermatology", "Dermatology"
    GENERAL_PRACTICE = "General Practice", "General Practice"
    PEDIATRICS = "Pediatrics", "Pediatrics"
    ORTHOPEDICS = "Orthopedics", "Orthopedics"
    PSYCHIATRY = "Psychiatry", "Psychiatry"
    PULMONOLOGY = "Pulmonology", "Pulmonology"
    GASTROENTEROLOGY = "Gastroenterology", "Gastroenterology"
    ENDOCRINOLOGY = "Endocrinology", "Endocrinology"

class WilayaEnum(models.TextChoices):
    ADRAR = "01", "Adrar"
    CHLEF = "02", "Chlef"
    LAGHOUAT = "03", "Laghouat"
    OUM_EL_BOUAGHI = "04", "Oum El Bouaghi"
    BATNA = "05", "Batna"
    BEJAIA = "06", "Béjaïa"
    BISKRA = "07", "Biskra"
    BECHAR = "08", "Béchar"
    BLIDA = "09", "Blida"
    BOUIRA = "10", "Bouira"
    TAMANRASSET = "11", "Tamanrasset"
    TEBESSA = "12", "Tébessa"
    TLEMCEN = "13", "Tlemcen"
    TIARET = "14", "Tiaret"
    TIZI_OUZOU = "15", "Tizi Ouzou"
    ALGIERS = "16", "Algiers"
    DJELFA = "17", "Djelfa"
    JIJEL = "18", "Jijel"
    SETIF = "19", "Sétif"
    SAIDA = "20", "Saïda"
    SKIKDA = "21", "Skikda"
    SIDI_BEL_ABBES = "22", "Sidi Bel Abbès"
    ANNABA = "23", "Annaba"
    GUELMA = "24", "Guelma"
    CONSTANTINE = "25", "Constantine"
    MEDEA = "26", "Médéa"
    MOSTAGANEM = "27", "Mostaganem"
    MSILA = "28", "M'sila"
    MASCARA = "29", "Mascara"
    OUARGLA = "30", "Ouargla"
    ORAN = "31", "Oran"
    EL_BAYADH = "32", "El Bayadh"
    ILLIZI = "33", "Illizi"
    BORDJ_BOU_ARRERIDJ = "34", "Bordj Bou Arréridj"
    BOUMERDES = "35", "Boumerdès"
    EL_TARF = "36", "El Tarf"
    TINDOUF = "37", "Tindouf"
    TISSEMSILT = "38", "Tissemsilt"
    EL_OUED = "39", "El Oued"
    KHENCHELA = "40", "Khenchela"
    SOUK_AHRAS = "41", "Souk Ahras"
    TIPAZA = "42", "Tipaza"
    MILA = "43", "Mila"
    AIN_DEFLA = "44", "Aïn Defla"
    NAAMA = "45", "Naâma"
    AIN_TEMOUCHENT = "46", "Aïn Témouchent"
    GHARDAIA = "47", "Ghardaïa"
    RELIZANE = "48", "Relizane"
    TIMIMOUN = "49", "Timimoun"
    BORDJ_BADJI_MOKHTAR = "50", "Bordj Badji Mokhtar"
    OULED_DJELLAL = "51", "Ouled Djellal"
    BENI_ABBES = "52", "Béni Abbès"
    IN_SALAH = "53", "In Salah"
    IN_GUEZZAM = "54", "In Guezzam"
    TOUGGOURT = "55", "Touggourt"
    DJANET = "56", "Djanet"
    EL_MGHAIER = "57", "El M'Ghair"
    EL_MENIAA = "58", "El Meniaa"



class PaymentMethod(models.TextChoices):
    BARIDIMOB= 'baridimob',
    CIB = 'cib',
    CASH = 'cash',

def user_pic_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    return os.path.join("pfps", str(instance.id), filename)

# Custom User Model
class CustomUser(AbstractUser):
    age = models.PositiveIntegerField()
    phone_number = models.CharField(max_length=20, unique=True)
    gender = models.CharField(max_length=10, choices=[('m', 'm'), ('f', 'f'), ('o', 'o')])
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    settings = models.JSONField(default=dict, blank=True)
    pic = models.ImageField(upload_to=user_pic_upload_path, null=True)
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
    
    # generate a unique filename using UUID
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
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
    response = models.TextField(blank=True, null=True)

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


# Payment Model
class Payment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    transaction_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=[('completed', 'completed'), ('failed', 'failed'), ('pending','pending')], default='completed')

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.status}"
    

class AppointedDoctor(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    specialty = models.CharField(
        max_length=50, choices= SpecialtyChoices.choices, default=SpecialtyChoices.GENERAL_PRACTICE
    )
    wilaya = models.CharField(
        max_length=50, choices=WilayaEnum.choices, default=WilayaEnum.CONSTANTINE
    )
    license_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=DoctorStatus.choices, default=DoctorStatus.ACTIVE, null=True)
    phone_number = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    email = models.EmailField()
    external_id = models.CharField(max_length=100, unique=True)

class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.notification_type} - {'Read' if self.is_read else 'Unread'}"