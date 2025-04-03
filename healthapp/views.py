from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.exceptions import MethodNotAllowed
from rest_framework import status, generics
from .models import *
from .serializers import *
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils.timezone import now
from django.db import transaction
from .permissions import *
from .ai_inference import ai_infer

# Create your views here.

# List and Create Users
class UserListCreateView(generics.ListCreateAPIView):
    queryset = CustomUser.objects.all()
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

    def get_queryset(self):
        return Appointment.objects.filter(user=self.request.user).order_by('appointment_date')

    def perform_create(self, serializer):
        user = self.request.user

        # Using a transaction to lock rows and prevent race conditions
        with transaction.atomic():
            existing_appointments = Appointment.objects.filter(
                user_id=self.request.user.id,
                appointment_date__gte=now(),
                status__in=['Pending', 'Confirmed']
            )
            if existing_appointments.exists():
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
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        appointment = self.get_object()
        if appointment.status != "pending":  
            return Response(
                {"detail": "You can only cancel pending appointments."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if appointment.appointment_date <= now() + timedelta(weeks=1):
            return Response(
                {"detail": "You can only delete appointments more than a week in the future."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)
    
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

        if appointment.status == 'completed':  
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

        # Retrieve the specified model
        ai_model = AIModel.objects.filter(id=model_id, status=AIModelStatus.DEPLOYED).first()
        if not ai_model:
            raise serializers.ValidationError({"error": "No deployed AI model found with the provided ID."})

        # Perform inference
        result, confidence = ai_infer(ai_model.model_file.path, scan)

        # Save the medical history record with AI interpretation
        serializer.save(user=user, scan=scan, ai_interpretation=f'{result}, confidence= {confidence:.2f}%')
        
        user.ai_tries -= 1
        user.save()

