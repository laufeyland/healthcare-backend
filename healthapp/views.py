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
from .tasks import send_to_fastapi
from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .tasks import notify_user_task

# Create your views here.

# List and Create Users
class UserListCreateView(generics.ListCreateAPIView):
    def get(self, request, *args, **kwargs):
        raise MethodNotAllowed("GET", detail="This action is not allowed.")
    
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# List Users
class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

# Retrieve, Update, and Delete a User by Admin
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]

# Retrieve and Update Account for Authenticated User
class AccountView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsUser | IsPatient]
    def get_object(self):
        return self.request.user

#Create Appointments for Authenticated User
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
            serializer.save(user=user)
# List Appointments for Authenticated User
class AppointmentListView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, IsUser | IsPatient]

    def get_queryset(self):
        return Appointment.objects.filter(user=self.request.user).order_by('appointment_date')

# Retrieve, Update, Delete a Specific Appointment by User
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

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        appointment = self.get_object()
        if appointment.status not in ['pending', 'confirmed']:  
            return Response(
                {"detail": "You can only cancel pending or confirmed appointments."},
                status=status.HTTP_400_BAD_REQUEST
            )
        appointment.status = AppointmentStatus.CANCELLED
        appointment.save()
        
    
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
    queryset = PremiumSubscription.objects.all()
    serializer_class = PremiumSubscriptionSerializer
    permission_classes = [IsAdmin]

    def perform_destroy(self, instance):
        user = instance.user
        user.premium_status = False
        if user.ai_tries > 5:
            user.ai_tries -= 5
        else:
            user.ai_tries = 0
        user.save()
        instance.delete()  

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

# Redeem Coupon
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
            serializer.save(user=user, appointment=latest_appointment)
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
        if not model_file.name.endswith('.h5', '.keras') or model_file.content_type not in ['application/octet-stream', 'application/x-hdf']:
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
    queryset = AIModel.objects.filter(status=AIModelStatus.DEPLOYED)
    serializer_class = AIModelSerializer
    permission_classes = [IsAuthenticated, IsUser | IsPatient]

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


# Tickets for Admin
class TicketListView(generics.ListAPIView):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [IsAdmin]

# Retrieve, Update, and Delete Ticket by Admin
class TicketDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [IsAdmin]

# Make a Ticket for users
class TicketCreateView(generics.CreateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated, IsUser | IsPatient]

    def perform_create(self, serializer):
        user = self.request.user
        Ticket_details = self.request.data.get("Ticket_details")
        if not Ticket_details:
            raise serializers.ValidationError({"error": "Ticket details are required."})
        serializer.save(user=user)

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(user=user).order_by('-created_at')

class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Notification.objects.filter(user=user)

    def perform_destroy(self, instance):
        instance.delete()

class PaymentCreateView(generics.CreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        amount = self.request.data.get("amount")
        if not amount:
            raise serializers.ValidationError({"error": "Amount is required."})
        serializer.save(user=user)
