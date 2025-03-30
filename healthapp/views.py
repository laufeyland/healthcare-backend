from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, generics
from .models import *
from .serializers import *
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated, IsAdminUser
from django.utils.timezone import now
from django.db import transaction
import logging

logger = logging.getLogger(__name__)
# Create your views here.

@api_view(['GET'])
def getUsers(request):
    users = CustomUser.objects.all()
    serializer = UserSerializer(users, many=True)
    permission_classes = (IsAuthenticatedOrReadOnly,)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([AllowAny])
def createUser(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def userDetail(request, pk):
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
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

            # Save the new appointment
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