from django.test import TestCase

# Create your tests here.

from healthapp.models import Appointment, CustomUser

# Replace with a real user ID from your database
user_id = 7
user = CustomUser.objects.get(id=user_id)  

# Get the latest appointment for the user
latest_appointment = Appointment.objects.filter(user=user).order_by('-appointment_date').first()

# Check if the appointment exists and is completed
if latest_appointment and latest_appointment.status == 'completed':
    print("OK")  # This means the condition passes
else:
    print("Patient must have a completed appointment before uploading a medical record.")

