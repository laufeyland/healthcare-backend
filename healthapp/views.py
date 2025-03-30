from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
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
    permission_classes = [IsAdminUser]

# Retrieve, Update, and Delete a User by Admin
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

# Retrieve and Update for Authenticated User
class AccountView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsUser]
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

# Retrieve, Update, Delete a Specific Appointment
class AppointmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(user=self.request.user)

# Filter Appointments by Status
class AppointmentByStatusView(generics.ListAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        status = self.kwargs.get('status')
        return Appointment.objects.filter(user=self.request.user, status=status)