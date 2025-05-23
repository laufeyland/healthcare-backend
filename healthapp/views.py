from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.exceptions import MethodNotAllowed
from rest_framework import status, generics
from rest_framework.views import APIView
from .models import *
from .serializers import *
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils.timezone import now, make_aware, is_naive
from django.db import transaction
from .permissions import *
from .tasks import *
from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .tasks import notify_user_task
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils.html import strip_tags


# Create your views here.

# Email Preview Example
def email_preview(request):
    context = {
        "subject": "Welcome to HealthCare!",
        "user_name": "Sarah Connor",
        "body_paragraphs": [
            "We’re thrilled to have you on board.",
            "You can now access your personal dashboard and manage your appointments easily.",
            "If you need any help, our support team is just a click away."
        ],
        "action_links": [
            {"url": "https://healthcare.example.com/dashboard", "label": "Go to Dashboard"},
            {"url": "https://healthcare.example.com/support", "label": "Contact Support"}
        ],
        "closing_remark": "Thanks for joining us and stay healthy!"
    }
    return render(request, "emails/notification_email.html", context)

# Example: Notify user when a new user is created
class UserListCreateView(generics.ListCreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Notify the user
            notify_user_task(user.id, "Your account has been successfully created.")
            
            # Send email notification
            subject = "Welcome to HealthCare!"
            template_name = "emails/notification_email.html"
            context = {
                "subject": subject,
                "user_name": user.username,
                "body_paragraphs": [
                    "We’re thrilled to have you on board.",
                    "You can now access your personal dashboard and manage your appointments easily.",
                    "If you need any help, our support team is just a click away."
                ],
                "action_links": [
                    {"url": "https://healthcare.example.com/dashboard", "label": "Go to Dashboard"},
                    {"url": "https://healthcare.example.com/support", "label": "Contact Support"}
                ],
                "closing_remark": "Thanks for joining us and stay healthy!"
            }
            send_email_task.delay(subject, [user.email], template_name, context)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# List Users
class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]


# Notify admin when a user is disabled
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.is_active == 0:
            return Response(
                {"detail": "User is already disabled."},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.is_active = 0
        user.save()
        # Notify the admin
        notify_user_task(request.user.id, f"User {user.id} has been disabled.")
        
        # Send email notification to admin
        subject = "User Disabled Notification"
        context = {
            "admin_username": request.user.username,
            "message": f"User {user.username} has been disabled."
        }
        send_email_task.delay(subject, [request.user.email], context)
        
        return Response({f"detail": "User {user.id} disabled"})

# Retrieve and Update Account for Authenticated User
class AccountView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsUser | IsPatient]
    def get_object(self):
        return self.request.user

# Example: Notify user when an appointment is created
class AppointmentListCreateView(generics.ListCreateAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        appointment_date_str = self.request.data.get("appointment_date")
        if not appointment_date_str:
            raise serializers.ValidationError({"error": "Appointment date is required."})
        
        try:
            appointment_date = datetime.fromisoformat(appointment_date_str)
        except ValueError:
            raise serializers.ValidationError({"error": "Invalid appointment date format. Use ISO 8601 format."})
        if is_naive(appointment_date):
            appointment_date = make_aware(appointment_date)
        appt_same_date = Appointment.objects.filter(appointment_date=appointment_date).first()
        if appt_same_date and appointment_date == appt_same_date.appointment_date and appt_same_date.status in ['pending', 'confirmed']:
            raise serializers.ValidationError({"error": "Appointment date already reserved."})
        if appointment_date <= now():
            raise serializers.ValidationError({"error": "Appointment date must be in the future."})
        if appointment_date > now() + timedelta(days=30):
            raise serializers.ValidationError({"error": "Appointment date must be within the next month."})
        if appointment_date.weekday() in [4, 5]:  
            raise serializers.ValidationError({"error": "Appointments cannot be made on Friday or Saturday."})
        if appointment_date.hour < 7 or appointment_date.hour > 17:
            raise serializers.ValidationError({"error": "Appointments can only be made between 7 AM and 5 PM."})
        if appointment_date.minute % 30 != 0:
            raise serializers.ValidationError({"error": "Appointments can only be made in 30-minute intervals."})
        
        # Using a transaction to lock rows and prevent race conditions
        with transaction.atomic():
            
            if Appointment.objects.filter(
                user_id=self.request.user.id,
                appointment_date__gte=now(),
                status__in=['pending', 'confirmed']
            ).exists():
                raise serializers.ValidationError(
                    {"error": "You already have a pending or confirmed appointment."}
                )
            appointment = serializer.save(user=user)
            # Notify the user
            notify_user_task(user.id, f"Your appointment on {appointment.appointment_date} has been successfully created.")
            
            # Send email notification
            subject = "Appointment Confirmation"
            template_name = "emails/notification_email.html"
            context = {
                "subject": subject,
                "user_name": user.username,
                "body_paragraphs": [
                    f"Your appointment has been successfully scheduled for {appointment.appointment_date}.",
                    "Please make sure to arrive on time and bring any necessary documents."
                ],
                "action_links": [
                    {"url": "https://healthcare.example.com/appointments", "label": "View Appointments"},
                    {"url": "https://healthcare.example.com/support", "label": "Contact Support"}
                ],
                "closing_remark": "Thank you for choosing HealthCare!"
            }
            send_email_task.delay(subject, [user.email], template_name, context)

# List Appointments for Authenticated User
class AppointmentListView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsUser | IsPatient]

    def get_queryset(self):
        return Appointment.objects.filter(user=self.request.user).order_by('appointment_date')

# Notify user when an appointment is updated or canceled
class AppointmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsUser | IsPatient]

    def get_queryset(self):
        return Appointment.objects.filter(user=self.request.user)
    def update(self, request, *args, **kwargs):
        appointment = self.get_object()
        request.data.pop('status', None)  # Remove status from request data
        if appointment.status != "pending":  
            return Response(
                {"detail": "You can only edit pending appointments."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if appointment.appointment_date <= now() + timedelta(weeks=1):
            return Response(
                {"detail": "You can only edit appointments more than a week in the future."},
                status=status.HTTP_400_BAD_REQUEST
            )
        appointment_date_str = request.data.get("appointment_date")
        if not appointment_date_str:
            raise serializers.ValidationError({"error": "Appointment date is required."})

        try:
            appointment_date = datetime.fromisoformat(appointment_date_str)
        except ValueError:
            raise serializers.ValidationError({"error": "Invalid appointment date format. Use ISO 8601 format."})

        if is_naive(appointment_date):
            appointment_date = make_aware(appointment_date)

        # Check if that date/time is already booked
        conflicting_appt = Appointment.objects.filter(
            appointment_date=appointment_date,
            status__in=["pending", "confirmed"]
        ).exclude(id=appointment.id).first()

        if conflicting_appt:
            raise serializers.ValidationError({"error": "Appointment date already reserved."})

        if appointment_date <= now():
            raise serializers.ValidationError({"error": "Appointment date must be in the future."})

        if appointment_date > now() + timedelta(days=30):
            raise serializers.ValidationError({"error": "Appointment date must be within the next month."})

        if appointment_date.weekday() in [4, 5]:
            raise serializers.ValidationError({"error": "Appointments cannot be made on Friday or Saturday."})

        if appointment_date.hour < 7 or appointment_date.hour > 17:
            raise serializers.ValidationError({"error": "Appointments can only be made between 7 AM and 5 PM."})

        if appointment_date.minute % 30 != 0:
            raise serializers.ValidationError({"error": "Appointments can only be made in 30-minute intervals."})

        response = super().update(request, *args, **kwargs)
        # Notify the user
        notify_user_task(self.request.user.id, f"Your appointment on {appointment.appointment_date} has been updated.")
        return response

    def destroy(self, request, *args, **kwargs):
        appointment = self.get_object()
        if appointment.status not in ['pending', 'confirmed']:  
            return Response(
                {"detail": "You can only cancel pending or confirmed appointments."},
                status=status.HTTP_400_BAD_REQUEST
            )
        appointment.status = AppointmentStatus.CANCELLED
        appointment.save()
        # Notify the user
        notify_user_task(self.request.user.id, f"Your appointment on {appointment.appointment_date} has been canceled.")
        return Response({"detail": "Appointment canceled."}, status=status.HTTP_204_NO_CONTENT)
        
    
    # List Appointments for Admin
class AppointmentsView(generics.ListAPIView):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAdmin]

# Retrieve, Update, and Delete an Appointment by Admin
class AppointmentEditView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAdmin]
    
    def perform_update(self, serializer):
        appointment = serializer.save()

        if appointment.status == 'finished':  
            user = appointment.user  
            if user.role not in ['patient', 'admin']:
                user.role = 'patient'
                user.save()

# Filter Appointments by Status for Authenticated User
class AppointmentByStatusView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsUser | IsPatient]

    def get_queryset(self):
        status = self.kwargs.get('status')
        return Appointment.objects.filter(user=self.request.user, status=status)

# Filter Appointments by Status for Admin
class AppointmentsStatusView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        status = self.kwargs.get('status')
        return Appointment.objects.filter(status=status)

# make a user premium by admin   
# Notify user when their premium subscription is created or revoked
class PremiumSubscriptionView(generics.CreateAPIView):
    serializer_class = PremiumSubscriptionSerializer
    permission_classes = [IsAdmin]  

    def perform_create(self, serializer):
        user_id = self.request.data.get("user_id")
        if not user_id:
            raise serializers.ValidationError({"error": "User ID is required."})

        user = get_object_or_404(User, id=user_id)

        # see if user already has an active premium subscription
        existing_subscription = PremiumSubscription.objects.filter(user=user).first()
        if existing_subscription and not existing_subscription.has_expired():
            raise serializers.ValidationError({"error": "User is already premium."})

        user.ai_tries += 5
        user.premium_status = True
        user.save()

        serializer.save(user=user)
        # Notify the user
        notify_user_task(user.id, "You have been upgraded to a premium subscription.")

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Bad API call. Use the revoke endpoint."},
            status=status.HTTP_400_BAD_REQUEST
        )

# List Premium Subscriptions for Admin
class PremiumSubscriptionListView(generics.ListAPIView):
    queryset = PremiumSubscription.objects.all()
    serializer_class = PremiumSubscriptionSerializer
    permission_classes = [IsAdmin]
    
# Revoke a user's premium status
class RevokePremiumView(generics.DestroyAPIView):
    permission_classes = [IsAdmin]

    def get_object(self):
        # Extract user_id from URL kwargs
        user_id = self.kwargs.get('user_id')

        # Fetch the CustomUser instance using the user_id
        return get_object_or_404(CustomUser, id=user_id)

    def perform_destroy(self, instance):
        # Update the user's premium status
        instance.premium_status = False
        instance.ai_tries = max(instance.ai_tries - 5, 0)  # Reduce AI tries if above 5
        instance.save()

        # Now find the PremiumSubscription associated with the user_id and delete it
        premium_subscription = get_object_or_404(PremiumSubscription, user=instance)
        premium_subscription.delete()
        # Notify the user
        notify_user_task(instance.id, "Your premium subscription has been revoked.")
        return Response({"detail": "Premium subscription revoked."}, status=status.HTTP_204_NO_CONTENT)
    

# Create coupons by admin
class CouponCreateView(generics.CreateAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsAdmin]

# List Coupons for Admin
class CouponListView(generics.ListAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsAdmin]

# Edit a Coupon by Admin
class CouponEditView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsAdmin]

# Notify user when a coupon is redeemed
class RedeemCouponView(generics.CreateAPIView):
    serializer_class = PremiumSubscriptionSerializer
    permission_classes = [IsAuthenticated]  

    def perform_create(self, serializer):
        user = self.request.user
        coupon_code = self.request.data.get("coupon_code")

        if not coupon_code:
            raise serializers.ValidationError({"error": "Coupon code is required."})

        # see if the user already has a premium subscription
        existing_subscription = PremiumSubscription.objects.filter(user=user).first()
        if existing_subscription and not existing_subscription.has_expired():
            raise serializers.ValidationError({"error": "User is already premium."})
        else:
            coupon = get_object_or_404(Coupon, coupon_code=coupon_code)

        user.ai_tries += 5
        user.premium_status = True
        user.save()
        coupon.delete()
        serializer.save(user=user)
        # Notify the user
        notify_user_task(user.id, "You have successfully redeemed a coupon and upgraded to premium.")

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed("DELETE", detail="This action is not allowed.")
    
# Medical History View for Authenticated User
class MedicalHistoryView(generics.ListCreateAPIView):
    serializer_class = MedicalHistorySerializer
    permission_classes = [IsAuthenticated, IsUser]

    def get_queryset(self):
        return MedicalHistory.objects.filter(user=self.request.user).order_by('-record_date')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# Medical History View for Admin
class MedicalHistoryAdminView(generics.ListAPIView):
    queryset = MedicalHistory.objects.all()
    serializer_class = MedicalHistorySerializer
    permission_classes = [IsAdmin]

# Retrieve Medical History by ID for Admin
class MedicalHistoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MedicalHistory.objects.all()
    serializer_class = MedicalHistorySerializer
    permission_classes = [IsAdmin]

# Retrieve Medical History by user ID for Admin
class MedicalHistoryByUserView(generics.ListAPIView):
    serializer_class = MedicalHistorySerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return MedicalHistory.objects.filter(user_id=user_id).order_by('-record_date')

# Upload Medical Record (post scans) by admin
class MedicalRecordUploadView(generics.CreateAPIView):
    serializer_class = MedicalHistorySerializer
    permission_classes = [IsAdmin]

    def perform_create(self, serializer):
        user_id = self.request.data.get("user")  # Extract patient ID from request
        image = self.request.FILES.get("scan")  # Extract image from request
        if not image:
            raise serializers.ValidationError({"error": "Image file is required."})
        if image.content_type not in ['image/jpeg', 'image/png']:
            raise serializers.ValidationError({"error": "Invalid image format. Only JPEG and PNG are allowed."})
        if not user_id:
            raise serializers.ValidationError({"error": "User (Patient) ID is required."})

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"error": "Patient not found."})

        latest_appointment = Appointment.objects.filter(
            user=user, status='finished'
        ).order_by('-appointment_date').first()

        if latest_appointment and latest_appointment.status == 'finished':
            latest_appointment.status = 'completed'
            latest_appointment.save()
            medical_record = serializer.save(user=user, appointment=latest_appointment)

            # Notify the user
            notify_user_task(user.id, "A new medical record has been uploaded to your account.")
            
            # Send email notification
            subject = "New Medical Record Uploaded"
            template_name = "emails/notification_email.html"
            context = {
                "subject": subject,
                "user_name": user.username,
                "body_paragraphs": [
                    "A new medical record has been uploaded to your account.",
                    "Please log in to your dashboard to view your updated medical history."
                ],
                "action_links": [
                    {"url": "https://healthcare.example.com/medical-history", "label": "View Medical History"},
                    {"url": "https://healthcare.example.com/support", "label": "Contact Support"}
                ],
                "closing_remark": "Thank you for trusting HealthCare with your health!"
            }
            send_email_task.delay(subject, [user.email], template_name, context)
        else:
            raise serializers.ValidationError({"error": "Patient must have a finished appointment before uploading a medical record."})
        
 # Upload AI Model
class AIModelCreateView(generics.CreateAPIView):
    queryset = AIModel.objects.all()
    serializer_class = AIModelSerializer
    permission_classes = [IsAdmin]

    def perform_create(self, serializer):
        model_file = self.request.FILES.get("model_file")
        if not model_file:
            raise serializers.ValidationError({"error": "Model file is required."})
        if not model_file.name.endswith(('.h5', '.keras')) or model_file.content_type not in ['application/octet-stream', 'application/x-hdf']:
            raise serializers.ValidationError({"error": "Invalid file type. Only .h5 model files are allowed."})
        serializer.save()
# View AI Models
class AIModelListView(generics.ListAPIView):
    queryset = AIModel.objects.all()
    serializer_class = AIModelSerializer
    permission_classes = [IsAdmin]

# Retrieve, Update, and Delete AI Model by Admin
class AIModelDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AIModel.objects.all()
    serializer_class = AIModelSerializer
    permission_classes = [IsAdmin]

# View Deployed AI Models
class DeployedAIModelView(generics.ListAPIView):
    
    serializer_class = AIModelSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        if self.request.user.role in ['user', 'patient']:
            return AIModel.objects.filter(status=AIModelStatus.DEPLOYED).order_by('-created_at')
        elif self.request.user.role == 'premium':
            # Allow premium users to see both deployed and VIP models
            return AIModel.objects.filter(status__in=[AIModelStatus.DEPLOYED, AIModelStatus.VIP]).order_by('-created_at')
        else:
            # For admin users, show all models
            return AIModel.objects.all().order_by('-created_at')

# AI Inference View for users uploading their own scans
class AiInferenceView(generics.CreateAPIView):
    serializer_class = MedicalHistorySerializer
    permission_classes = [IsAuthenticated, IsUser | IsPatient]

    def perform_create(self, serializer):
        user = self.request.user
        if user.ai_tries <= 0:
            raise serializers.ValidationError({"error": "You have no AI tries left."})

        scan = self.request.FILES.get("scan")
        model_id = self.request.data.get("model_id")

        if not scan:
            raise serializers.ValidationError({"error": "Scan file is required."})
        if scan.content_type not in ['image/jpeg', 'image/png']:
            raise serializers.ValidationError({"error": "Invalid image format. Only JPEG and PNG are allowed."})
        if not model_id:
            raise serializers.ValidationError({"error": "Model ID is required."})

        # Retrieve AI model
        ai_model = AIModel.objects.filter(id=model_id, status=AIModelStatus.DEPLOYED).first()
        if not ai_model:
            raise serializers.ValidationError({"error": "No deployed AI model found with the provided ID."})
        
        history = serializer.save(user=user, scan=scan, ai_interpretation="Processing...")
        image_path = history.scan.path
        task = send_to_fastapi.delay(ai_model.model_file.path, image_path)
        if not task:
            raise serializers.ValidationError({"error": "Failed to send image for inference."})
        
        # Retrieve the response from the task
        result = task.get(timeout=30)  # Wait for up to 30 seconds for the task to complete
        if result.get("error"):
            raise serializers.ValidationError({"error": result["error"]})
        
        diagnosis = result.get("predicted_label")
        confidence = result.get("confidence")
        if not diagnosis or confidence is None:
            raise serializers.ValidationError({"error": "Invalid response from AI model."})
        
        history.ai_interpretation = {
            "diagnosis": diagnosis,
            "confidence": confidence
        }
        history.task_id = task.id
        history.save()

        user.ai_tries -= 1
        user.save()

        # Notify the user
        notify_user_task(user.id, "Your AI inference results are ready.")
        
        # Send email notification
        subject = "AI Inference Results Ready"
        template_name = "emails/notification_email.html"
        context = {
            "subject": subject,
            "user_name": user.username,
            "body_paragraphs": [
                f"Your AI inference results are ready.",
                f"Diagnosis: {diagnosis}",
                f"Confidence: {confidence:.2f}%"
            ],
            "action_links": [
                {"url": "https://healthcare.example.com/ai-results", "label": "View Results"},
                {"url": "https://healthcare.example.com/support", "label": "Contact Support"}
            ],
            "closing_remark": "Thank you for using HealthCare!"
        }
        send_email_task.delay(subject, [user.email], template_name, context)

class AiInferenceHView(APIView):
    permission_classes = [IsAuthenticated, IsUser | IsPatient]

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.ai_tries <= 0:
            return Response({"error": "You have no AI tries left."}, status=400)

        medical_history_id = request.data.get("history_id")
        model_id = request.data.get("model_id")

        if not medical_history_id or not model_id:
            return Response({"error": "history_id and model_id are required."}, status=400)

        try:
            history = MedicalHistory.objects.get(id=medical_history_id, user=user)
        except MedicalHistory.DoesNotExist:
            return Response({"error": "Medical record not found."}, status=404)

        if not history.scan:
            return Response({"error": "No scan found in the selected medical history."}, status=400)

        ai_model = AIModel.objects.filter(id=model_id, status=AIModelStatus.DEPLOYED).first()
        if not ai_model:
            return Response({"error": "No deployed AI model found with the provided ID."}, status=400)

        image_path = history.scan.path
        task = send_to_fastapi.delay(ai_model.model_file.path, image_path)

        result = task.get(timeout=30)
        if result.get("error"):
            return Response({"error": result["error"]}, status=500)

        diagnosis = result.get("predicted_label")
        confidence = result.get("confidence")
        if not diagnosis or confidence is None:
            return Response({"error": "Invalid response from AI model."}, status=500)

        history.ai_interpretation = {
            "diagnosis": diagnosis,
            "confidence": confidence
        }
        history.task_id = task.id
        history.save()

        user.ai_tries -= 1
        user.save()

        return Response({
            "message": "AI inference completed.",
            "result": history.ai_interpretation
        })


# Retrieve, Update, and Delete Ticket by Admin
class TicketDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [IsAdmin]

# Ticket list for User
class TicketListView(generics.ListAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Ticket.objects.all()
        elif user.role == 'patient':
            return Ticket.objects.filter(reported_by=user)
        else:
            return Ticket.objects.none()

# Notify user when a ticket is created
class TicketCreateView(generics.CreateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated, IsUser | IsPatient]

    def perform_create(self, serializer):
        user = self.request.user
        subject = self.request.data.get("subject")
        if not subject:
            raise serializers.ValidationError({"error": "Subject is required."})
        Ticket_details = self.request.data.get("description")
        if not Ticket_details:
            raise serializers.ValidationError({"error": "Ticket details are required."})
        ticket = serializer.save(reported_by=user)
        # Notify the user
        notify_user_task(user.id, f"Your ticket with ID {ticket.id} has been successfully created.")


class PaymentCreateView(generics.CreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        amount = self.request.data.get("amount")
        if not amount:
            raise serializers.ValidationError({"error": "Amount is required."})
        serializer.save(user=user)

class SyncAppointedDoctorsView(APIView):
    serializer_class = AppointedDoctor
    permission_classes = [IsAdmin]
    def post(self, request, *args, **kwargs):
        user_id = request.user.id
        task = sync_appointed_doctors.delay(user_id)

        try:
            task.get(timeout=30)  
        except Exception as e:
            return Response({"error": str(e)}, status=500)
        if task.result.get("error"):
            return Response({"error": task.result["error"]}, status=500)
        

        return Response({"message": "Sync Complete"}, status=status.HTTP_202_ACCEPTED)
    
# Notify user when their password is changed
class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsUser | IsPatient]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        user = self.get_object()
        old_password = self.request.data.get("old_password")
        new_password = self.request.data.get("new_password")
        if not old_password:
            raise serializers.ValidationError({"error": "Old password is required."})
        if not new_password:
            raise serializers.ValidationError({"error": "New password is required."})
        if not user.check_password(old_password):
            raise serializers.ValidationError({"error": "Old password is incorrect."})
        user.set_password(new_password)
        user.save()
        # Notify the user
        notify_user_task(user.id, "Your password has been successfully changed.")
        
        # Send email notification
        subject = "Password Change Notification"
        template_name = "emails/notification_email.html"  # Add the template name
        context = {
            "subject": subject,
            "user_name": user.username,
            "body_paragraphs": [
                "Your password has been successfully changed.",
                "If you did not make this change, please contact support immediately."
            ],
            "action_links": [
                {"url": "https://healthcare.example.com/support", "label": "Contact Support"}
            ],
            "closing_remark": "Thank you for using HealthCare!"
        }
        send_email_task.delay(subject, [user.email], template_name, context)  # Pass the template_name argument
        
        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)
    


# Notify user when AI tries are updated
class IncreaseAiTries(generics.UpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        set_tries = self.request.data.get("ai_tries")
        if not set_tries:
            raise serializers.ValidationError({"error" : "Must insert the number of AI tries"})
        user = self.get_object()
        user.ai_tries = set_tries
        user.save()
        # Notify the user
        notify_user_task(user.id, f"Your AI tries have been updated to {user.ai_tries}.")
        return Response({"message": f"AI Tries set successfully to {user.ai_tries}"}, status=status.HTTP_200_OK)
    
class AppointedDoctorListView(generics.ListAPIView):
    queryset = AppointedDoctor.objects.all()
    serializer_class = AppointedDoctorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AppointedDoctor.objects.all().order_by('first_name')

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


from django.shortcuts import render

def email_preview(request):
    context = {
        "subject": "Welcome to HealthCare!",
        "user_name": "Sarah Connor",
        "body_paragraphs": [
            "We’re thrilled to have you on board.",
            "You can now access your personal dashboard and manage your appointments easily.",
            "If you need any help, our support team is just a click away."
        ],
        "action_links": [
            {"url": "https://healthcare.example.com/dashboard", "label": "Go to Dashboard"},
            {"url": "https://healthcare.example.com/support", "label": "Contact Support"}
        ],
        "closing_remark": "Thanks for joining us and stay healthy!"
    }
    return render(request, "emails/notification_email.html", context)


class ReservedAppointmentDatesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Get all appointments with reserved statuses
        reserved_appointments = Appointment.objects.filter(
            status__in=['pending', 'confirmed']
            ).values_list('appointment_date', flat=True)

        # Convert datetimes to ISO 8601 strings
        reserved_dates = [dt.isoformat() for dt in reserved_appointments]

        return Response({"reserved_dates": reserved_dates})