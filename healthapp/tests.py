from django.test import TestCase

# Create your tests here.
from django.utils.timezone import now
from healthapp.models import * # Adjust based on your project

user = CustomUser.objects.get(id="3")  # Replace with an actual username
existing_appointments = Appointment.objects.filter(
    user_id=user.request.user.id,
    appointment_date__gte=now(),
    status__in=['Pending', 'Confirmed']
)
print(existing_appointments)
