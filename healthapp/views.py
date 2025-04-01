from django.shortcuts import get_object_or_404, render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import MethodNotAllowed
from rest_framework import status, generics
from .models import *
from .serializers import *
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated, IsAdminUser
from django.utils.timezone import now
from django.db import transaction
from .permissions import *
import logging

logger = logging.getLogger(__name__)
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
   
class AppointmentListCreateView(generics.ListCreateAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(user=self.request.user).order_by('appointment_date')

    def perform_create(self, serializer):
        user = self.request.user

        # Using a transaction to lock rows and prevent race conditions
        with transaction.atomic():
            existing_appointments = Appointment.objects.select_for_update().filter(
                user_id=self.request.user.id,
                appointment_date__gte=now(),
                status__in=['Pending', 'Confirmed']
            )

            logger.debug(f"Checking for existing appointments for user {user}: {existing_appointments}")

            if existing_appointments.exists():
                raise serializers.ValidationError(
                    {"error": "You already have a pending or confirmed appointment."}
                )
            serializer.save(user=user)

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

        # Check if the coupon exists
        coupon = get_object_or_404(Coupon, coupon_code=coupon_code)

        # see if the user already has a premium subscription
        existing_subscription = PremiumSubscription.objects.filter(user=user).first()
        if existing_subscription and not existing_subscription.has_expired():
            raise serializers.ValidationError({"error": "User is already premium."})


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
        return MedicalHistory.objects.filter(patient=self.request.user).order_by('-record_date')

    def perform_create(self, serializer):
        serializer.save(patient=self.request.user)

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
        return MedicalHistory.objects.filter(patient_id=user_id).order_by('-record_date')

# Upload Medical Record (post scans) by admin
class MedicalRecordUploadView(generics.CreateAPIView):
    serializer_class = MedicalHistorySerializer
    permission_classes = [IsAdmin]

    def perform_create(self, serializer):
        user = self.request.user

        # Get the latest appointment for the user
        latest_appointment = Appointment.objects.filter(patient=user).order_by('-date').first()

        # Check if there's an appointment and if it's marked as completed
        if latest_appointment and latest_appointment.status == 'completed':
            # Proceed with saving the medical record
            serializer.save()
        else:
            raise serializers.ValidationError({"error": "Patient must have a completed appointment before uploading a medical record."})

